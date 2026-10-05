using System.Collections;
using System.Collections.Generic;
using CCEPL_CAD.Models;
using DG.Tweening;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.Video;

namespace CCEPL_CAD
{
    public class UIManager : MonoBehaviour
    {
        RefManager _refManager => RefManager.Instance;
        UIReference _uiRef;
        Faults _faults;

        private int StepPerform = -1;
        private int maxAttempt = 3;
        private List<FaultTab> _faultTabs = new();
        private List<FaultStep> _faultSteps = new();
        private List<Tool> _tools = new();
        [SerializeField] private List<int> _stepsAttempt;
        
        private bool leftOpen = false;
        private bool rightOpen = false;
        
        private Vector2 toolsPanelOpenPos;
        private Vector2 toolsPanelClosedPos;

        private Vector2 modesPanelOpenPos;
        private Vector2 modesPanelClosedPos;
        Tween _faultAnimation;
        private Tool _tool;
        private bool splashFinished = false;
        internal ToolObject _selectedTool;

        IEnumerator Start()
        {
            yield return null;
            
            toolsPanelOpenPos = _uiRef.ToolPanel.anchoredPosition;
            modesPanelOpenPos = _uiRef.FaultPanel.anchoredPosition;
            toolsPanelClosedPos = toolsPanelOpenPos + Vector2.left * (_uiRef.ToolPanel.rect.width + 50);
            modesPanelClosedPos = modesPanelOpenPos + Vector2.right * (_uiRef.FaultPanel.rect.width + 50);
            
            _uiRef.ToolPanel.anchoredPosition = toolsPanelClosedPos;
            _uiRef.FaultPanel.anchoredPosition = modesPanelClosedPos;
        }

        private void OnEnable()
        {
            _uiRef = _refManager.UIReference;
            _uiRef.ToolsBtn.onClick.AddListener(ToggleToolsUI);
            _uiRef.ToolsBackBtn.onClick.AddListener(ToggleToolsUI);
            _uiRef.ModesBtn.onClick.AddListener(ToggleModesUI);
            _uiRef.ModesBackBtn.onClick.AddListener(ToggleModesUI);

            _uiRef.RepairedFaultSubmitBtn.onClick.AddListener(SubmitRepairedFault);

            _uiRef.SkipFaultStepBtn.onClick.AddListener(() => SkipCurrentStep(true));
            _uiRef.BackStepBtn.onClick.AddListener(PreviousStep);
            _uiRef.FaultResetBtn.onClick.AddListener(()=>
            {
                ResetUI();
            });
            _uiRef.TestModeToggle.onValueChanged.AddListener((state) =>
            {
                _uiRef.TestModeToggleText.color = state ? Color.red : Color.black;
                _uiRef.ModeBGImage.sprite = state ? _uiRef.TestModeBGSprite : _uiRef.ExamModeBGSprite;
                _uiRef.HiddenObjectForExamMode.ForEach(x => x.SetActive(state));
                LayoutRebuilder.ForceRebuildLayoutImmediate(_uiRef.ModeBGImage.rectTransform);
            });
            _uiRef.ExamModeToggle.onValueChanged.AddListener((state) =>
                _uiRef.ExamModeToggleText.color = state ? Color.red : Color.black);
            
            if(_uiRef.VideoPanel != null && _uiRef.VideoPlayer != null && _uiRef.VideoPlayer.clip != null)
            {
                _uiRef.VideoPanel.gameObject.SetActive(true);
                _uiRef.VideoPlayer.loopPointReached += VideoPlayeManager;
            }

            EventManager.OnToolSelected += ToolSelect;
            EventManager.OnFaultDetect += FaultDetect;
            EventManager.OnFaultClick += OnFaultClick;
            EventManager.OnStepComplete += OnStepComplete;
            EventManager.OnWrongToolSelected += WrongToolSelected;
            EventManager.OnLogMessage += OnLogMessage;
            EventManager.TriggerDisplayText += DisaplayStepMessage;

            _uiRef.SkipFaultStepBtn.gameObject.SetActive(RefManager.Instance.FaultManager.Modes == Modes.Easy);
            _uiRef.BackStepBtn.gameObject.SetActive(RefManager.Instance.FaultManager.Modes == Modes.Easy);

            Init();
        }

        void OnLogMessage(string text, bool isError)
        {
            DisaplayMessage(text, isError ? _uiRef.FailureMessageTextColor : _uiRef.SuccessMessageTextColor,
                isError ? _uiRef.FailureMessageBGColor : _uiRef.SuccessMessageBGColor,
                isError ? _uiRef.FailureMessageOutlineColor : _uiRef.SuccessMessageOutlineColor);
        }

        private void OnDisable()
        {
            _uiRef.ToolsBtn.onClick.RemoveAllListeners();
            _uiRef.ToolsBackBtn.onClick.RemoveAllListeners();
            _uiRef.ModesBtn.onClick.RemoveAllListeners();
            _uiRef.ModesBackBtn.onClick.RemoveAllListeners();
            _uiRef.RepairedFaultSubmitBtn.onClick.RemoveAllListeners();
            _uiRef.SkipFaultStepBtn.onClick.RemoveAllListeners();
            _uiRef.BackStepBtn.onClick.RemoveAllListeners();
            _uiRef.FaultResetBtn.onClick.RemoveAllListeners();
            _uiRef.VideoPlayer.loopPointReached -= VideoPlayeManager;
            EventManager.OnToolSelected -= ToolSelect;
            EventManager.OnFaultDetect -= FaultDetect;
            EventManager.OnFaultClick -= OnFaultClick;
            EventManager.OnStepComplete -= OnStepComplete;
            EventManager.OnWrongToolSelected -= WrongToolSelected;
            EventManager.OnLogMessage -= OnLogMessage;
            EventManager.TriggerDisplayText -= DisaplayStepMessage;
        }

        private void ToggleToolsUI()
        {
            leftOpen = !leftOpen;
            var seq = DOTween.Sequence();
            seq.Append(_uiRef.ToolPanel.DOAnchorPos(leftOpen ? toolsPanelOpenPos : toolsPanelClosedPos, 0.5f));
            seq.Join(_uiRef.ToolPanel.DOScale(leftOpen ? 1f : 0.95f, 0.5f));
            seq.SetEase(Ease.OutBack);
        }

        void ToggleModesUI()
        {
            rightOpen = !rightOpen;
            var seq = DOTween.Sequence();
            seq.Append(_uiRef.FaultPanel.DOAnchorPos(rightOpen ? modesPanelOpenPos : modesPanelClosedPos, 0.5f));
            seq.Join(_uiRef.FaultPanel.DOScale(rightOpen ? 1f : 0.95f, 0.5f));
            seq.SetEase(Ease.OutBack);
        }

        void ToolSelect(ToolType toolType, ToolObject toolObject)
        {
            //_uiRef.ToolPanel.SetActive(false);
            if (_tool._toolType == toolType) _tool = null;
            _tools.ForEach(x => x.ResetSelection());
            _uiRef.MessageObj.gameObject.SetActive(false);
        }

        void OnStepComplete()
        {
            if(!RefManager.Instance.FaultManager.IsFaultStart) return;
            _tools.ForEach(x => x.ResetSelection());
            _faultSteps[StepPerform].OnStepComplete();
            StepPerform++;
            _stepsAttempt[^ 1]++;
            //Debug.Log($"{StepPerform} steps complete");
            CheckAllStepAreCompleted();
        }

        private void CheckAllStepAreCompleted()
        {
            _uiRef.FaultDisplayObj.gameObject.SetActive(false);
            if (_faultAnimation != null)
            {
                _faultAnimation.Kill();
                _faultAnimation = null;
            }
            if (StepPerform >= _faultSteps.Count)
            {
                _uiRef.RepairedFaultSubmitBtn.interactable = true;
                _uiRef.SkipFaultStepBtn.interactable = false;
                _uiRef.BackStepBtn.interactable = false;
                _uiRef.FaultResetBtn.interactable = false;
                EventManager.OnLogMessage?.Invoke("Fault Repaired Successfully", false);
                Debug.LogError($"Attempts {JsonConvert.SerializeObject(_stepsAttempt.ToArray())}");
            }
            else
            {
                var step = _faultSteps[StepPerform];
                _uiRef.SkipFaultStepBtn.interactable = step.IsSkippable();
                _uiRef.BackStepBtn.interactable = StepPerform > 0;
                step.OnStepStart();
                
                _tool = _tools.Find(x => x._toolType == step.Step.RequireToolType);
                if(step.IsSkippable()) _tool.HighLightTool();
                _stepsAttempt.Add(0);
            }
        }

        internal FaultStep GetCurrentFaultStep()
        {
            return StepPerform >= _faultSteps.Count || StepPerform == -1 ? null : _faultSteps[StepPerform];
        }


        void Init()
        {
            //Disable all panels
            //_uiRef.ToolPanel.gameObject.SetActive(false);
            //_uiRef.FaultPanel.gameObject.SetActive(false);
            _uiRef.ComponentPanel.gameObject.SetActive(false);
            _uiRef.MessageObj.gameObject.SetActive(false);
            _uiRef.RepairedFaultSubmitBtn.interactable = false;
            _uiRef.RepairedFaultSubmitBtn.transform.parent.gameObject.SetActive(false);
            _uiRef.RepairedFaultSubmitBtn.interactable = false;
            _uiRef.SkipFaultStepBtn.interactable = true;
            _uiRef.BackStepBtn.interactable = false;
            _uiRef.FaultResetBtn.interactable = true;

            //Testmode is default
            _uiRef.TestModeToggle.SetIsOnWithoutNotify(true);
            _uiRef.ExamModeToggle.SetIsOnWithoutNotify(false);

            //Tools Instantiate
            foreach (var toolsData in _refManager.ToolsDataSo.ToolsData)
            {
                if(toolsData.ToolObject == null) continue;
                var tool = Instantiate(_uiRef.ToolPrefab, _uiRef.ToolParent);
                tool.SetTool(new ToolData()
                {
                    ToolIcon = toolsData.ToolIcon, 
                    ToolName = toolsData.ToolType.ToString(),
                    ToolType = toolsData.ToolType,
                    ToolObject = toolsData.ToolObject
                });
                _tools.Add(tool);
            }
        }

        void FaultDetect(Faults faults)
        {
            this._faults = faults;
            foreach (var fault in faults.FaultList)
            {
                var faultTab = Instantiate(_uiRef.FaultTabPrefab, _uiRef.FaultTabParent);
                faultTab.Init(fault.FaultIndex);
                _faultTabs.Add(faultTab);
            }
        }

        void OnFaultClick(int faultIndex)
        {
            if(RefManager.Instance.FaultManager.IsFaultStart)
            {
                EventManager.OnLogMessage?.Invoke("Please finish the selected fault first.", true);
                return;
            }
            RefManager.Instance.FaultManager.IsFaultStart = true;
            var faultData = _faults.FaultList.Find(x => x.FaultIndex == faultIndex);
            if (faultData == null) return;
            _faultTabs.ForEach(x => x.ResetGraphics());
            _faultTabs.Find(x => x._faultIndex == faultIndex).SelectTab();
            _uiRef.FaultDescription.text = faultData.Message;
            foreach (var fault in faultData.Steps)
            {
                var stepTemp = Instantiate(_uiRef.FaultStepPrefab, _uiRef.FaultStepParent);
                stepTemp.SetFault(fault);
                _faultSteps.Add(stepTemp);
            }

            var step = _faultSteps[0];
            _uiRef.MessageObj.gameObject.SetActive(false);
            step.OnStepStart();
            StepPerform = 0;
            _stepsAttempt = new List<int> { 0 };
            
            _uiRef.RepairedFaultSubmitBtn.transform.parent.gameObject.SetActive(true);
            _uiRef.RepairedFaultSubmitBtn.interactable = false;
            _uiRef.SkipFaultStepBtn.interactable = true;
            _uiRef.FaultResetBtn.interactable = true;
            _uiRef.BackStepBtn.interactable = false;

            _tool = _tools.Find(x => x._toolType == step.Step.RequireToolType);
            if(step.IsSkippable()) _tool.HighLightTool();
        }

        void WrongToolSelected()
        {
            EventManager.OnLogMessage?.Invoke("Wrong tool selected. Please select a right tool.", true);
            if (_stepsAttempt.Count > 0) _stepsAttempt[^ 1]++;
            if (_stepsAttempt[^ 1] >= maxAttempt) SkipCurrentStep();
        }

        void SkipCurrentStep(bool isSkipped = false)
        {
            if (StepPerform < 0 || StepPerform >= _faultSteps.Count) return;

            _tools.ForEach(x => x.ResetSelection(true));

            // Lock button during animation to prevent duplicate triggers
            _uiRef.SkipFaultStepBtn.interactable = false;
            _uiRef.BackStepBtn.interactable = false;

            if (isSkipped)
            {
                if (_stepsAttempt.Count > 0)
                    _stepsAttempt[^1] = 0;
                
                _faultSteps[StepPerform].OnStepSkip();
                if (_selectedTool)
                {
                    DestroyImmediate(_selectedTool.gameObject, true);
                    HandleToolOperation.Instance._tool = null;
                    _selectedTool = null;
                }
            }
            else _faultSteps[StepPerform].OnStepReject();

            var currentStep = _faultSteps[StepPerform];
            var animDuration = currentStep.Step.AnimationClip ? currentStep.Step.AnimationClip.length + 2f : 2f;

            RefManager.Instance.FaultManager.PlayStepAnimation(currentStep.Step, false);

            _faultAnimation = DOVirtual.DelayedCall(animDuration, () =>
            {
                _faultAnimation = null;
                StepPerform++;
                CheckAllStepAreCompleted();
            });
        }

        void PreviousStep()
        {
            if (StepPerform <= 0 || StepPerform > _faultSteps.Count) return;

            // Lock UI buttons during back-step animation to prevent duplicate calls
            _uiRef.SkipFaultStepBtn.interactable = false;
            _uiRef.BackStepBtn.interactable = false;

            _tools.ForEach(x => x.ResetSelection(true));

            if (_selectedTool)
            {
                DestroyImmediate(_selectedTool.gameObject, true);
                HandleToolOperation.Instance._tool = null;
                _selectedTool = null;
            }

            // Reset visual state of current step if within bounds
            if (StepPerform < _faultSteps.Count)
            {
                _faultSteps[StepPerform].OnStepReject();
            }

            // Step back to previous step index
            StepPerform--;

            if (_stepsAttempt != null && _stepsAttempt.Count > 1)
            {
                _stepsAttempt.RemoveAt(_stepsAttempt.Count - 1);
            }

            var targetStep = _faultSteps[StepPerform];
            targetStep.OnStepReject();

            if (targetStep.Step != null && targetStep.Step.AnimationClip != null)
            {
                var animDuration = targetStep.Step.AnimationClip ? targetStep.Step.AnimationClip.length + 2f : 2f;
                RefManager.Instance.FaultManager.PlayStepAnimation(targetStep.Step, false, isReverse: true);

                if (_faultAnimation != null)
                {
                    _faultAnimation.Kill();
                    _faultAnimation = null;
                }

                _faultAnimation = DOVirtual.DelayedCall(animDuration, () =>
                {
                    _faultAnimation = null;
                    CheckAllStepAreCompleted();
                });
            }
            else
            {
                CheckAllStepAreCompleted();
            }
        }

        void SubmitRepairedFault()
        {
            EventManager.SubmitFault?.Invoke(ByteConverter.ConvertListToBytes(_stepsAttempt));
            ResetUI();
        }

        private void ResetUI()
        {
            if (_faultAnimation != null)
            {
                _faultAnimation.Kill();
                _faultAnimation = null;
            }
            RefManager.Instance.FaultManager.IsFaultStart = false;
            _uiRef.RepairedFaultSubmitBtn.transform.parent.gameObject.SetActive(false);
            
            if (_selectedTool)
            {
                DestroyImmediate(_selectedTool.gameObject, true);
                _selectedTool = null;
                HandleToolOperation.Instance._tool = null;
            }
            _uiRef.RepairedFaultSubmitBtn.interactable = false;
            _uiRef.SkipFaultStepBtn.interactable = true;
            _uiRef.FaultResetBtn.interactable = true;
            _uiRef.BackStepBtn.interactable = false;
            
            _uiRef.FaultDisplayObj.gameObject.SetActive(false);
            _faultSteps.ForEach(b =>
            {
                b.OnStepReject();
                DestroyImmediate(b.gameObject);
            });
            _faultSteps.Clear();
            _faultTabs.ForEach(x => x.ResetGraphics());
            _uiRef.FaultDescription.text = string.Empty;
            _tools.ForEach(x => x.ResetSelection(true));
            EventManager.OnFaultCompleted?.Invoke();
        }

        void DisaplayMessage(string message, Color textColor, Color bgColor, Color borderColor)
        {
            _uiRef.MessageText.text = message;
            _uiRef.MessageText.color = textColor;
            _uiRef.MessageObj.color = bgColor;
            _uiRef.MessageOutline.effectColor = borderColor;
            _uiRef.MessageObj.gameObject.SetActive(true);
            
            DOVirtual.DelayedCall(2f, () => _uiRef.MessageObj.gameObject.SetActive(false));
        }

        private void DisaplayStepMessage(string obj)
        {
            _uiRef.FaultDisplayText.text = obj;
            _uiRef.FaultDisplayObj.gameObject.SetActive(true);
            _uiRef.FaultDisplayText.color = Color.blue;
        }

        void VideoPlayeManager(VideoPlayer source)
        {
            if (splashFinished)
                return;

            splashFinished = true;
            _uiRef.VideoPanel.gameObject.SetActive(false);
        }
    }
}