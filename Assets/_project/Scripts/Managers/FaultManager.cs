using System;
using System.Collections;
using System.Collections.Generic;
using CCEPL_CAD.Models;
using DG.Tweening;
using Newtonsoft.Json;
using RuntimeSceneGizmo;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace CCEPL_CAD
{
    public class FaultManager : MonoBehaviour
    {
        public Modes Modes = Modes.Easy;
        public Faults faults;
        internal bool IsFaultStart = false;
        
        // Playables Graph for standalone animation handling (Forward & Reverse)
        private PlayableGraph customGraph;
        private AnimationMixerPlayable customMixer;
        private bool isCustomGraphCreated = false;
        private Coroutine animationCoroutine;
        private Animator targetAnimator;

        private void Awake()
        {
            Application.targetFrameRate = 120;
        }

        private void OnEnable()
        {
            EventManager.OnFaultsReceived += FaultsReceived;
            EventManager.OnFaultCompleted += CleanupCustomGraph;
            EventManager.ResetAnimation += CleanupCustomGraph;
            DOVirtual.DelayedCall(3f, () => { EventManager.OnFaultDetect?.Invoke(faults); });
        }

        private void OnDisable()
        {
            EventManager.OnFaultsReceived -= FaultsReceived;
            EventManager.OnFaultCompleted -= CleanupCustomGraph;
            EventManager.ResetAnimation -= CleanupCustomGraph;
            CleanupCustomGraph();
        }

        private void Start()
        {
            EventManager.StartApplication?.Invoke();
        }

        void FaultsReceived(string data)
        {
            Debug.Log($"[FaultManager] \n{JsonConvert.SerializeObject(data, Formatting.Indented)}");
        }

        [Header("Visual Inspection Settings")]
        [SerializeField] private float visualInspectionDuration = 5.5f;

        public static bool IsVisualInspectionStep(Step step)
        {
            if (step == null) return false;
            ToolType t = step.RequireToolType;
            return t == ToolType.Visual ||
                   t == ToolType.VisualCheck ||
                   t == ToolType.VisualCheckInThroghtSightGlass ||
                   t == ToolType.VisualInspection ||
                   t == ToolType.VisualInspectionLamp ||
                   t == ToolType.None;
        }

        #region Fault steps

        internal void PlayStepAnimation(Step step, bool state = true, bool isReverse = false)
        {
            ResetStepHighlights();
            if (animationCoroutine != null) StopCoroutine(animationCoroutine);
            animationCoroutine = StartCoroutine(ExecuteAnimationRoutine(step, state, isReverse));
            if(step.IsDisplayeText) EventManager.TriggerDisplayText(step.DisaplayMessage);
        }

        private void ResetStepHighlights()
        {
            
        }

        private IEnumerator ExecuteAnimationRoutine(Step step, bool state = true, bool isReverse = false)
        {
            // Lock camera movement during visual inspection / step execution
            EventManager.OnCameraLockStateChanged?.Invoke(true);
            CameraMovement.OnCameraLockStateChanged?.Invoke(true);

            // Move camera to specific position and rotation if configured for this step
            if (step != null && step.UseCustomCameraTransform)
            {
                EventManager.MoveCameraToTransform?.Invoke(step.TargetCameraPosition, step.TargetCameraRotation, 1.0f);
            }

            float duration = 1.0f;
            bool isVisualStep = IsVisualInspectionStep(step);

            if (step != null && step.AnimationClip != null)
            {
                float clipLength = step.AnimationClip.length;
                float absSpeed = Mathf.Max(0.001f, Mathf.Abs(step.AnimationSpeed));
                duration = clipLength / absSpeed;

                if (isVisualStep && !isReverse)
                {
                    yield return new WaitForSeconds(3);
                    duration = Mathf.Max(duration, visualInspectionDuration);
                }

                var playSpeed = isReverse ? step.AnimationSpeed * -1 : step.AnimationSpeed;
                Debug.Log(
                    $"[FaultManager] Playing clip '{step.AnimationClip.name}' | Reverse: {isReverse} | Speed: {playSpeed} | Duration: {duration:F2}s");
                PlayClipWithPlayable(step.AnimationClip, playSpeed);
            }
            else
            {
                duration = isVisualStep ? visualInspectionDuration : 2f;
                Debug.Log($"[FaultManager] Step '{(step != null ? step.Message : "null")}' | Visual: {isVisualStep} | Duration: {duration:F2}s");
            }

            yield return new WaitForSeconds(duration);

            // Unlock camera movement
            EventManager.OnCameraLockStateChanged?.Invoke(false);
            CameraMovement.OnCameraLockStateChanged?.Invoke(false);

            if (state) EventManager.OnStepComplete?.Invoke();
        }

        private void CompleteProcedure()
        {
            ResetStepHighlights();
            EventManager.OnFaultCompleted?.Invoke();
        }

        // --- PLAYABLE GRAPH ANIMATION PLAYBACK (FORWARD & REVERSE) ---

        private void PlayClipWithPlayable(AnimationClip clip, float speed)
        {
            targetAnimator = CustomizedUIBase.Instance?.Animator;

            if (!targetAnimator) return;
            
            EnsureCustomGraphCreated();

            var clipPlayable = AnimationClipPlayable.Create(customGraph, clip);
            clipPlayable.SetApplyFootIK(false);
            clipPlayable.SetApplyPlayableIK(false);

            if (customMixer.GetInputCount() == 0)
            {
                customGraph.Connect(clipPlayable, 0, customMixer, 0);
            }
            else
            {
                customGraph.Disconnect(customMixer, 0);
                customGraph.Connect(clipPlayable, 0, customMixer, 0);
            }

            customMixer.SetInputWeight(0, 1f);

            if (speed < 0f)
            {
                clipPlayable.SetTime(clip.length);
                clipPlayable.SetSpeed(speed);
            }
            else
            {
                clipPlayable.SetTime(0);
                clipPlayable.SetSpeed(speed);
            }

            customGraph.Play();
        }

        private void EnsureCustomGraphCreated()
        {
            if (isCustomGraphCreated && customGraph.IsValid()) return;

            customGraph = PlayableGraph.Create("RepairWorkflowGraph");
            customGraph.SetTimeUpdateMode(DirectorUpdateMode.GameTime);

            customMixer = AnimationMixerPlayable.Create(customGraph, 1);

            if (targetAnimator != null)
            {
                var output = AnimationPlayableOutput.Create(customGraph, "AnimationOutput", targetAnimator);
                output.SetSourcePlayable(customMixer);
            }

            isCustomGraphCreated = true;
        }

        public void CleanupCustomGraph()
        {
            if (isCustomGraphCreated && customGraph.IsValid())
            {
                customGraph.Destroy();
                isCustomGraphCreated = false;
            }
        }

        #endregion

        #region Step Copy & Append Utilities

        /// <summary>
        /// Copies all steps from source Fault and appends them to target Fault's existing Steps list.
        /// </summary>
        public int AppendStepsFromFault(int sourceFaultIndex, int targetFaultIndex)
        {
            if (faults == null || faults.FaultList == null) return 0;
            if (sourceFaultIndex < 0 || sourceFaultIndex >= faults.FaultList.Count) return 0;
            if (targetFaultIndex < 0 || targetFaultIndex >= faults.FaultList.Count) return 0;

            return AppendStepsFromFault(faults.FaultList[sourceFaultIndex], faults.FaultList[targetFaultIndex]);
        }

        /// <summary>
        /// Copies all steps from source Fault and appends them to target Fault's existing Steps list.
        /// </summary>
        public int AppendStepsFromFault(Fault sourceFault, Fault targetFault)
        {
            if (sourceFault == null || targetFault == null) return 0;
            if (sourceFault.Steps == null || sourceFault.Steps.Count == 0) return 0;

            if (targetFault.Steps == null)
            {
                targetFault.Steps = new List<Step>();
            }

            int count = 0;
            foreach (var step in sourceFault.Steps)
            {
                if (step != null)
                {
                    targetFault.Steps.Add(step.Clone());
                    count++;
                }
            }

            return count;
        }

        /// <summary>
        /// Appends a collection of steps (cloned) to a target Fault's existing Steps list.
        /// </summary>
        public int AppendSteps(Fault targetFault, IEnumerable<Step> stepsToAppend)
        {
            if (targetFault == null || stepsToAppend == null) return 0;
            if (targetFault.Steps == null)
            {
                targetFault.Steps = new List<Step>();
            }

            int count = 0;
            foreach (var step in stepsToAppend)
            {
                if (step != null)
                {
                    targetFault.Steps.Add(step.Clone());
                    count++;
                }
            }

            return count;
        }

        #endregion
    }
}