using TMPro;
using UnityEngine;
using UnityEngine.UI;
using UIOutline = UnityEngine.UI.Outline;

namespace CCEPL_CAD
{
    public class FaultTab : MonoBehaviour
    {
        public Button FaultBtn;
        public TMP_Text FaultName;
        public UIOutline Outline;
        public Color DefaultOutlineColor;
        public Color SelectedOutlineColor;
        internal int _faultIndex = -1;
        public bool IsFaultCompleted;

        private void OnEnable()
        {
            FaultBtn.onClick.AddListener(OnFaultClick);
        }

        private void OnDisable()
        {
            FaultBtn.onClick.RemoveAllListeners();
        }

        public void Init(int faultIndex)
        {
            _faultIndex = faultIndex;
            FaultName.text = $"Fault {faultIndex}";
        }

        void OnFaultClick()
        {
            EventManager.OnFaultClick?.Invoke(_faultIndex);
        }

        internal void ResetGraphics()
        {
            FaultBtn.interactable = true;
            Outline.effectColor = DefaultOutlineColor;
        }

        internal void SelectTab()
        {
            FaultBtn.interactable = false;
            Outline.effectColor = SelectedOutlineColor;
        }
    }
}