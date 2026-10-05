using System.Collections.Generic;
using UnityEngine;

namespace CCEPL_CAD
{
    public abstract class CustomizedUIBase : MonoBehaviour
    {
        public static CustomizedUIBase Instance;
        
        [Header("Base Animator Settings")]
        public Animator Animator;
        public RuntimeAnimatorController AnimatorController;
        public RuntimeAnimatorController FaultAnimatorController;

        [Header("Base UI Canvas Group")]
        public CanvasGroup CustomUICanvas;
        public bool IsCustomUIVisible = true;

        [Header("Idle State Objects")]
        public List<GameObject> IdleObjects = new List<GameObject>();

        protected virtual void Awake()
        {
            Instance = this;
            InitializeBaseAnimator();
        }

        protected virtual void Start()
        {
            UpdateCanvasVisibility(IsCustomUIVisible);
        }

        protected virtual void OnEnable()
        {
            EventManager.ReceivedUDPData += OnReceiveUDPData;
            EventManager.OnFaultsReceived += OnReceiveRawUDPString;
            EventManager.OnFaultClick += TriggerFault;
            EventManager.OnFaultCompleted += OnFaultCompleted;
            EventManager.ResetAnimation += ResetAnimation;
        }

        protected virtual void OnDisable()
        {
            EventManager.ReceivedUDPData -= OnReceiveUDPData;
            EventManager.OnFaultsReceived -= OnReceiveRawUDPString;
            EventManager.OnFaultClick -= TriggerFault;
            EventManager.OnFaultCompleted -= OnFaultCompleted;
            EventManager.ResetAnimation -= ResetAnimation;
        }

        protected virtual void InitializeBaseAnimator()
        {
            if (Animator == null)
            {
                Animator = GetComponentInChildren<Animator>();
            }

            if (Animator != null && AnimatorController != null)
            {
                Animator.runtimeAnimatorController = AnimatorController;
            }
        }

        public virtual void UpdateCanvasVisibility(bool isVisible)
        {
            if (CustomUICanvas != null)
            {
                CustomUICanvas.alpha = isVisible ? 1f : 0f;
                CustomUICanvas.blocksRaycasts = isVisible;
            }
        }

        public virtual void TriggerFault(int faultIndex)
        {
            if (Animator == null || FaultAnimatorController == null) return;

            UpdateCanvasVisibility(false);

            foreach (var idleObject in IdleObjects)
            {
                if (idleObject != null) idleObject.SetActive(false);
            }

            Animator.runtimeAnimatorController = FaultAnimatorController;
        }

        public virtual void OnFaultCompleted()
        {
            UpdateCanvasVisibility(IsCustomUIVisible);

            foreach (var idleObject in IdleObjects)
            {
                if (idleObject != null) idleObject.SetActive(true);
            }

            if (Animator != null && AnimatorController != null)
            {
                Animator.enabled = false;
                Animator.runtimeAnimatorController = AnimatorController;
                Animator.enabled = true;
            }

            ResetAnimation();
        }

        public abstract void ResetAnimation();
        protected abstract void OnReceiveUDPData(List<float> values);
        protected virtual void OnReceiveRawUDPString(string raw) { }
    }
}