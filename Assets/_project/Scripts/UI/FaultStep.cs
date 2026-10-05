using CCEPL_CAD.Models;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using UIOutline =  UnityEngine.UI.Outline;

namespace CCEPL_CAD
{
    public class FaultStep : MonoBehaviour
    {
        public TMP_Text FaultText;
        public Image FaultStepBG;
        public UIOutline FaultStepBGOutline;
        public Color FaultStepCompColor;
        public Color FaultStepCompOutlineColor;
        public Color FaultStepRejectColor;
        public Color FaultStepRejectOutlineColor;
        public Color FaultStepSkipColor;
        public Color FaultStepSkipOutlineColor;
        public Color FaultStepStartColor;
        public Color DefaultColor;
        private string _componentCode;
        private ToolType _requireTool;
        internal Step Step;

        internal void SetFault(Step step)
        {
            _componentCode = step.ComponentCode;
            _requireTool = step.RequireToolType;
            FaultText.text =
                $"{step.Message}{(RefManager.Instance.FaultManager.Modes == Modes.Easy ? $" ({ByteConverter.SplitWords(_requireTool.ToString())})" : string.Empty)}";
            FaultStepBG.color = DefaultColor;
            Step = step;
        }

        internal void OnStepStart()
        {
            FaultStepBG.color = FaultStepStartColor;
            if (FaultManager.IsVisualInspectionStep(Step)) RefManager.Instance.FaultManager.PlayStepAnimation(Step);
            HighLightAllTargets();
        }

        internal void OnStepComplete()
        {
            ApplyStateVisuals(FaultStepCompColor, FaultStepCompOutlineColor);
        }

        internal void OnStepReject()
        {
            ApplyStateVisuals(FaultStepRejectColor, FaultStepRejectOutlineColor);
            ResetAllTargets();
        }

        internal void OnStepSkip()
        {
            ApplyStateVisuals(FaultStepSkipColor, FaultStepSkipOutlineColor);
            ResetAllTargets();
        }

        internal bool IsToolMatch(ToolType tool, string code)
        {
            return _requireTool == tool;
        }

        internal bool IsSkippable()
        {
            return !FaultManager.IsVisualInspectionStep(Step);
        }

        #region Helper Methods

        private void ApplyStateVisuals(Color bgColor, Color outlineColor)
        {
            if (FaultStepBG != null)
            {
                FaultStepBG.color = bgColor;
            }

            if (FaultStepBGOutline != null)
            {
                // Direct assignment avoids allocating a zero-second DOTween instance
                FaultStepBGOutline.effectColor = outlineColor;
            }
        }

        private void ResetAllTargets()
        {
            if (Step?.Targets == null) return;
            
            foreach (var target in Step.Targets)
            {
                if (target) target.OnObjectReset();
            }
        }

        private void HighLightAllTargets()
        {
            if (Step?.Targets == null) return;
            
            foreach (var target in Step.Targets)
            {
                if (target) target.OnObjectDeselected();
            }
        }

        #endregion
    }
}