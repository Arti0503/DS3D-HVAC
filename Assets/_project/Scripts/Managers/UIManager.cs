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
        private int _currentFaultIndex = -1;
        public int CurrentFaultIndex => _currentFaultIndex;
        private int maxAttempt = 3;
        private List<FaultTab> _faultTabs = new();
        private List<FaultStep> _faultSteps = new();
        private List<Tool> _tools = new();
        [SerializeField] private List<int> _stepsAttempt;
        [SerializeField] private List<int> _wrongAttemptsPerStep = new();
        
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

        private bool _positionsInitialized = false;

        private void EnsurePanelPositions()
        {
            if (_positionsInitialized) return;
            if (_uiRef == null || _uiRef.ToolPanel == null || _uiRef.FaultPanel == null) return;

            toolsPanelOpenPos = _uiRef.ToolPanel.anchoredPosition;
            modesPanelOpenPos = _uiRef.FaultPanel.anchoredPosition;
            toolsPanelClosedPos = toolsPanelOpenPos + Vector2.left * (_uiRef.ToolPanel.rect.width + 50);
            modesPanelClosedPos = modesPanelOpenPos + Vector2.right * (_uiRef.FaultPanel.rect.width + 50);
            _positionsInitialized = true;
        }

        IEnumerator Start()
        {
            yield return null;
            EnsurePanelPositions();
            _uiRef.ToolPanel.anchoredPosition = toolsPanelClosedPos;
            _uiRef.FaultPanel.anchoredPosition = modesPanelClosedPos;
            leftOpen = false;
            rightOpen = false;
        }

        private void OnEnable()
        {
            _uiRef = _refManager.UIReference;
            _uiRef.ToolsBtn.onClick.AddListener(ToggleToolsUI);
            _uiRef.ToolsBackBtn.onClick.AddListener(ToggleToolsUI);
            _uiRef.ModesBtn.onClick.AddListener(ToggleModesUI);
            _uiRef.ModesBackBtn.onClick.AddListener(ToggleModesUI);

            _uiRef.RepairedFaultSubmitBtn.onClick.AddListener(SubmitRepairedFault);

            // [REMOVED FROM UI] Skip, BackStep, and UI Reset buttons disabled/commented out
            // if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.onClick.AddListener(() => SkipCurrentStep(true));
            // if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.onClick.AddListener(PreviousStep);
            // if (_uiRef.FaultResetBtn != null) _uiRef.FaultResetBtn.onClick.AddListener(() => ResetUI());

            // Remove control buttons from exam mode toggle list so toggling modes never re-shows them
            if (_uiRef.HiddenObjectForExamMode != null)
            {
                _uiRef.HiddenObjectForExamMode.RemoveAll(x => x == null || 
                    (_uiRef.SkipFaultStepBtn != null && x == _uiRef.SkipFaultStepBtn.gameObject) || 
                    (_uiRef.BackStepBtn != null && x == _uiRef.BackStepBtn.gameObject) || 
                    (_uiRef.FaultResetBtn != null && x == _uiRef.FaultResetBtn.gameObject));
            }

            _uiRef.TestModeToggle.onValueChanged.AddListener((state) =>
            {
                _uiRef.TestModeToggleText.color = state ? Color.red : Color.black;
                _uiRef.ModeBGImage.sprite = state ? _uiRef.TestModeBGSprite : _uiRef.ExamModeBGSprite;
                _uiRef.HiddenObjectForExamMode.ForEach(x => x.SetActive(state));
                LayoutRebuilder.ForceRebuildLayoutImmediate(_uiRef.ModeBGImage.rectTransform);
                HideRemovedControlButtons();
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
            EventManager.RequestTriggerFault += TriggerFaultFromNetwork;
            EventManager.RequestResetFault += ResetUI;
            // EventManager.RequestSkipStep += HandleSkipRequest;
            // EventManager.RequestPreviousStep += PreviousStep;

            HideRemovedControlButtons();

            Init();
        }

        private void HideRemovedControlButtons()
        {
            if (_uiRef == null) return;
            if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.gameObject.SetActive(false);
            if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.gameObject.SetActive(false);
            if (_uiRef.FaultResetBtn != null) _uiRef.FaultResetBtn.gameObject.SetActive(false);
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
            // if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.onClick.RemoveAllListeners();
            // if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.onClick.RemoveAllListeners();
            // if (_uiRef.FaultResetBtn != null) _uiRef.FaultResetBtn.onClick.RemoveAllListeners();
            _uiRef.VideoPlayer.loopPointReached -= VideoPlayeManager;
            EventManager.OnToolSelected -= ToolSelect;
            EventManager.OnFaultDetect -= FaultDetect;
            EventManager.OnFaultClick -= OnFaultClick;
            EventManager.OnStepComplete -= OnStepComplete;
            EventManager.OnWrongToolSelected -= WrongToolSelected;
            EventManager.OnLogMessage -= OnLogMessage;
            EventManager.TriggerDisplayText -= DisaplayStepMessage;
            EventManager.RequestTriggerFault -= TriggerFaultFromNetwork;
            EventManager.RequestResetFault -= ResetUI;
            // EventManager.RequestSkipStep -= HandleSkipRequest;
            // EventManager.RequestPreviousStep -= PreviousStep;
        }

        /*
        private void HandleSkipRequest()
        {
            SkipCurrentStep(true);
        }
        */

        public void SetToolsUI(bool open, bool animate = true)
        {
            EnsurePanelPositions();
            if (leftOpen == open) return;
            leftOpen = open;
            if (animate && _uiRef != null && _uiRef.ToolPanel != null)
            {
                var seq = DOTween.Sequence();
                seq.Append(_uiRef.ToolPanel.DOAnchorPos(leftOpen ? toolsPanelOpenPos : toolsPanelClosedPos, 0.45f));
                seq.Join(_uiRef.ToolPanel.DOScale(leftOpen ? 1f : 0.95f, 0.45f));
                seq.SetEase(Ease.OutBack);
            }
            else if (_uiRef != null && _uiRef.ToolPanel != null)
            {
                _uiRef.ToolPanel.anchoredPosition = leftOpen ? toolsPanelOpenPos : toolsPanelClosedPos;
                _uiRef.ToolPanel.localScale = leftOpen ? Vector3.one : new Vector3(0.95f, 0.95f, 1f);
            }
        }

        public void SetModesUI(bool open, bool animate = true)
        {
            EnsurePanelPositions();
            if (rightOpen == open) return;
            rightOpen = open;
            if (animate && _uiRef != null && _uiRef.FaultPanel != null)
            {
                var seq = DOTween.Sequence();
                seq.Append(_uiRef.FaultPanel.DOAnchorPos(rightOpen ? modesPanelOpenPos : modesPanelClosedPos, 0.45f));
                seq.Join(_uiRef.FaultPanel.DOScale(rightOpen ? 1f : 0.95f, 0.45f));
                seq.SetEase(Ease.OutBack);
            }
            else if (_uiRef != null && _uiRef.FaultPanel != null)
            {
                _uiRef.FaultPanel.anchoredPosition = rightOpen ? modesPanelOpenPos : modesPanelClosedPos;
                _uiRef.FaultPanel.localScale = rightOpen ? Vector3.one : new Vector3(0.95f, 0.95f, 1f);
            }
        }

        private void ToggleToolsUI() => SetToolsUI(!leftOpen);
        void ToggleModesUI() => SetModesUI(!rightOpen);

        private void ScrollToFaultTab(FaultTab targetTab)
        {
            if (targetTab == null || _uiRef == null || _uiRef.FaultTabParent == null) return;

            var scrollRect = _uiRef.FaultTabParent.GetComponentInParent<ScrollRect>();
            if (scrollRect == null || scrollRect.content == null || scrollRect.viewport == null) return;

            DOVirtual.DelayedCall(0.05f, () =>
            {
                if (targetTab == null || scrollRect == null || scrollRect.content == null || scrollRect.viewport == null) return;

                Canvas.ForceUpdateCanvases();
                LayoutRebuilder.ForceRebuildLayoutImmediate(scrollRect.content);

                RectTransform targetRect = targetTab.GetComponent<RectTransform>();
                if (targetRect == null) return;

                float contentWidth = scrollRect.content.rect.width;
                float viewportWidth = scrollRect.viewport.rect.width;
                if (contentWidth <= viewportWidth) return;

                Vector3 localPos = scrollRect.content.InverseTransformPoint(targetRect.position);
                float childCenterX = localPos.x - scrollRect.content.rect.xMin;
                float halfView = viewportWidth * 0.5f;
                float targetScroll = Mathf.Clamp(childCenterX - halfView, 0f, contentWidth - viewportWidth);
                float normalized = Mathf.Clamp01(targetScroll / (contentWidth - viewportWidth));

                DOTween.To(() => scrollRect.horizontalNormalizedPosition, x => scrollRect.horizontalNormalizedPosition = x, normalized, 0.4f)
                    .SetEase(Ease.OutCubic);
            });
        }

        private void ScrollToTool(Tool targetTool)
        {
            if (targetTool == null || _uiRef == null || _uiRef.ToolParent == null) return;

            var scrollRect = _uiRef.ToolParent.GetComponentInParent<ScrollRect>();
            if (scrollRect == null || scrollRect.content == null || scrollRect.viewport == null) return;

            DOVirtual.DelayedCall(0.05f, () =>
            {
                if (targetTool == null || scrollRect == null || scrollRect.content == null || scrollRect.viewport == null) return;

                Canvas.ForceUpdateCanvases();
                LayoutRebuilder.ForceRebuildLayoutImmediate(scrollRect.content);

                RectTransform targetRect = targetTool.GetComponent<RectTransform>();
                if (targetRect == null) return;

                float contentHeight = scrollRect.content.rect.height;
                float viewportHeight = scrollRect.viewport.rect.height;
                if (contentHeight <= viewportHeight) return;

                Vector3 localPos = scrollRect.content.InverseTransformPoint(targetRect.position);
                float childDistFromTop = Mathf.Abs(localPos.y);
                float halfView = viewportHeight * 0.5f;
                float targetScroll = Mathf.Clamp(childDistFromTop - halfView, 0f, contentHeight - viewportHeight);
                float normalized = 1f - Mathf.Clamp01(targetScroll / (contentHeight - viewportHeight));

                DOTween.To(() => scrollRect.verticalNormalizedPosition, x => scrollRect.verticalNormalizedPosition = x, normalized, 0.4f)
                    .SetEase(Ease.OutCubic);
            });
        }

        private void ScrollToStep(FaultStep targetStep)
        {
            if (targetStep == null || _uiRef == null || _uiRef.FaultStepParent == null) return;

            var scrollRect = _uiRef.FaultStepParent.GetComponentInParent<ScrollRect>();
            if (scrollRect == null || scrollRect.content == null || scrollRect.viewport == null) return;

            DOVirtual.DelayedCall(0.05f, () =>
            {
                if (targetStep == null || scrollRect == null || scrollRect.content == null || scrollRect.viewport == null) return;

                Canvas.ForceUpdateCanvases();
                LayoutRebuilder.ForceRebuildLayoutImmediate(scrollRect.content);

                RectTransform targetRect = targetStep.GetComponent<RectTransform>();
                if (targetRect == null) return;

                float contentHeight = scrollRect.content.rect.height;
                float viewportHeight = scrollRect.viewport.rect.height;
                if (contentHeight <= viewportHeight) return;

                Vector3 localPos = scrollRect.content.InverseTransformPoint(targetRect.position);
                float childDistFromTop = Mathf.Abs(localPos.y);
                float halfView = viewportHeight * 0.5f;
                float targetScroll = Mathf.Clamp(childDistFromTop - halfView, 0f, contentHeight - viewportHeight);
                float normalized = 1f - Mathf.Clamp01(targetScroll / (contentHeight - viewportHeight));

                DOTween.To(() => scrollRect.verticalNormalizedPosition, x => scrollRect.verticalNormalizedPosition = x, normalized, 0.4f)
                    .SetEase(Ease.OutCubic);
            });
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

            int stepNumber = StepPerform + 1;
            int wrongAttempts = (StepPerform < _wrongAttemptsPerStep.Count) ? _wrongAttemptsPerStep[StepPerform] : 0;
            int totalSteps = _faultSteps.Count;
            bool isLastStep = (StepPerform + 1 >= _faultSteps.Count);

            StepPerform++;

            EventManager.OnStepAccomplished?.Invoke(_currentFaultIndex, stepNumber, wrongAttempts, totalSteps, isLastStep);

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
                if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.interactable = false;
                if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.interactable = false;
                if (_uiRef.FaultResetBtn != null) _uiRef.FaultResetBtn.interactable = false;
                EventManager.OnLogMessage?.Invoke("Fault Repaired Successfully", false);
                Debug.LogError($"Attempts {JsonConvert.SerializeObject(_wrongAttemptsPerStep.ToArray())}");

                EventManager.OnFaultFinished?.Invoke(_currentFaultIndex, _faultSteps.Count, new List<int>(_wrongAttemptsPerStep));
            }
            else
            {
                var step = _faultSteps[StepPerform];
                if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.interactable = step.IsSkippable();
                if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.interactable = StepPerform > 0;
                step.OnStepStart();
                ScrollToStep(step);
                
                _tool = _tools.Find(x => x._toolType == step.Step.RequireToolType);
                if(step.IsSkippable() && _tool != null)
                {
                    _tool.HighLightTool();
                    ScrollToTool(_tool);
                }
            }
            HideRemovedControlButtons();
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
            if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.interactable = true;
            if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.interactable = false;
            if (_uiRef.FaultResetBtn != null) _uiRef.FaultResetBtn.interactable = true;
            HideRemovedControlButtons();

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

        public void TriggerFaultFromNetwork(int faultCode)
        {
            EnsureFaultsLoaded();
            if (_faults == null || _faults.FaultList == null)
            {
                Debug.LogError($"[UIManager] Cannot trigger fault {faultCode}: Fault list is not loaded yet.");
                return;
            }

            var faultData = _faults.FaultList.Find(x => x.FaultIndex == faultCode);
            if (faultData == null)
            {
                Debug.LogWarning($"[UIManager] Fault code {faultCode} not found in FaultList.");
                return;
            }

            if (RefManager.Instance.FaultManager.IsFaultStart)
            {
                ResetUI();
            }

            OnFaultClick(faultCode);
        }

        private void EnsureFaultsLoaded()
        {
            if (_faults == null && RefManager.Instance != null && RefManager.Instance.FaultManager != null)
            {
                _faults = RefManager.Instance.FaultManager.faults;
            }
        }

        void OnFaultClick(int faultIndex)
        {
            if(RefManager.Instance.FaultManager.IsFaultStart)
            {
                EventManager.OnLogMessage?.Invoke("Please finish the selected fault first.", true);
                return;
            }
            EnsureFaultsLoaded();
            if (_faults == null || _faults.FaultList == null) return;

            var faultData = _faults.FaultList.Find(x => x.FaultIndex == faultIndex);
            if (faultData == null) return;

            // Automatically open both Tool Panel (left) and Fault/Modes Panel (right)
            SetToolsUI(true);
            SetModesUI(true);

            _currentFaultIndex = faultIndex;
            RefManager.Instance.FaultManager.IsFaultStart = true;
            _faultTabs.ForEach(x => x.ResetGraphics());
            var matchingTab = _faultTabs.Find(x => x._faultIndex == faultIndex);
            if (matchingTab != null)
            {
                matchingTab.SelectTab();
                ScrollToFaultTab(matchingTab);
            }

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
            ScrollToStep(step);
            StepPerform = 0;
            _wrongAttemptsPerStep = new List<int>();
            _stepsAttempt = new List<int>();
            for (int i = 0; i < _faultSteps.Count; i++)
            {
                _wrongAttemptsPerStep.Add(0);
                _stepsAttempt.Add(0);
            }
            
            _uiRef.RepairedFaultSubmitBtn.transform.parent.gameObject.SetActive(true);
            _uiRef.RepairedFaultSubmitBtn.interactable = false;
            if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.interactable = true;
            if (_uiRef.FaultResetBtn != null) _uiRef.FaultResetBtn.interactable = true;
            if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.interactable = false;
            HideRemovedControlButtons();

            _tool = _tools.Find(x => x._toolType == step.Step.RequireToolType);
            if(step.IsSkippable() && _tool != null)
            {
                _tool.HighLightTool();
                ScrollToTool(_tool);
            }

            EventManager.OnFaultStarted?.Invoke(faultIndex, _faultSteps.Count);
        }

        void WrongToolSelected()
        {
            EventManager.OnLogMessage?.Invoke("Wrong tool selected. Please select a right tool.", true);
            if (StepPerform >= 0 && StepPerform < _wrongAttemptsPerStep.Count)
            {
                _wrongAttemptsPerStep[StepPerform]++;
                if (StepPerform < _stepsAttempt.Count)
                {
                    _stepsAttempt[StepPerform] = _wrongAttemptsPerStep[StepPerform];
                }

                if (_wrongAttemptsPerStep[StepPerform] >= maxAttempt)
                {
                    SkipCurrentStep();
                }
            }
        }

        void SkipCurrentStep(bool isSkipped = false)
        {
            if (StepPerform < 0 || StepPerform >= _faultSteps.Count) return;

            _tools.ForEach(x => x.ResetSelection(true));

            // Lock button during animation to prevent duplicate triggers
            if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.interactable = false;
            if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.interactable = false;

            int stepNumber = StepPerform + 1;
            int totalSteps = _faultSteps.Count;
            bool isLastStep = (StepPerform + 1 >= _faultSteps.Count);
            int wrongAttempts = isSkipped ? 0 : ((StepPerform < _wrongAttemptsPerStep.Count) ? _wrongAttemptsPerStep[StepPerform] : maxAttempt);

            if (isSkipped)
            {
                _faultSteps[StepPerform].OnStepSkip();
                if (_selectedTool)
                {
                    DestroyImmediate(_selectedTool.gameObject, true);
                    HandleToolOperation.Instance._tool = null;
                    _selectedTool = null;
                }
            }
            else
            {
                _faultSteps[StepPerform].OnStepReject();
            }

            var currentStep = _faultSteps[StepPerform];
            var animDuration = currentStep.Step.AnimationClip ? currentStep.Step.AnimationClip.length + 2f : 2f;

            RefManager.Instance.FaultManager.PlayStepAnimation(currentStep.Step, false);

            _faultAnimation = DOVirtual.DelayedCall(animDuration, () =>
            {
                _faultAnimation = null;
                StepPerform++;
                EventManager.OnStepAccomplished?.Invoke(_currentFaultIndex, stepNumber, wrongAttempts, totalSteps, isLastStep);
                CheckAllStepAreCompleted();
            });
        }

        /*
        void PreviousStep()
        {
            if (StepPerform <= 0 || StepPerform > _faultSteps.Count) return;

            // Lock UI buttons during back-step animation to prevent duplicate calls
            if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.interactable = false;
            if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.interactable = false;

            _tools.ForEach(x => x.ResetSelection(true));

            if (_selectedTool)
            {
                DestroyImmediate(_selectedTool.gameObject, true);
                HandleToolOperation.Instance._tool = null;
                _selectedTool = null;
            }

            // Reset visual state of forward step being backed out of
            if (StepPerform < _faultSteps.Count)
            {
                _faultSteps[StepPerform].OnStepReset();
            }

            // Step back to previous step index
            StepPerform--;

            var targetStep = _faultSteps[StepPerform];
            targetStep.OnStepReject();

            // Give the code of the last step completed to LabVIEW:
            int lastCompletedStep = StepPerform;
            int wrongAttemptsOnLastCompleted = (lastCompletedStep > 0 && lastCompletedStep - 1 < _wrongAttemptsPerStep.Count)
                ? _wrongAttemptsPerStep[lastCompletedStep - 1]
                : 0;
            int totalSteps = _faultSteps.Count;

            EventManager.OnStepAccomplished?.Invoke(_currentFaultIndex, lastCompletedStep, wrongAttemptsOnLastCompleted, totalSteps, false);

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
        */

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
            _currentFaultIndex = -1;
            _wrongAttemptsPerStep?.Clear();
            _stepsAttempt?.Clear();
            _uiRef.RepairedFaultSubmitBtn.transform.parent.gameObject.SetActive(false);
            
            if (_selectedTool)
            {
                DestroyImmediate(_selectedTool.gameObject, true);
                _selectedTool = null;
                HandleToolOperation.Instance._tool = null;
            }
            _uiRef.RepairedFaultSubmitBtn.interactable = false;
            if (_uiRef.SkipFaultStepBtn != null) _uiRef.SkipFaultStepBtn.interactable = true;
            if (_uiRef.FaultResetBtn != null) _uiRef.FaultResetBtn.interactable = true;
            if (_uiRef.BackStepBtn != null) _uiRef.BackStepBtn.interactable = false;
            HideRemovedControlButtons();
            
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
            SetToolsUI(false);
            SetModesUI(false);
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