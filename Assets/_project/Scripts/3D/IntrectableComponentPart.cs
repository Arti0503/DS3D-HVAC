using System;
using CCEPL_CAD.Models;
using UnityEngine;
using UnityEngine.EventSystems;

namespace CCEPL_CAD
{
    [RequireComponent(typeof(Outline))]
    public class IntrectableComponentPart : MonoBehaviour, IPointerDownHandler
    {
        public InteractableComponentData InteractableComponentData;
        internal bool IsTriggered = false;
        private Color _outlineColor = new Color(0, 0, 0, 0f);
        private Outline _outline;
        private Collider _collider;

        private void OnValidate()
        {
            _outline = GetComponent<Outline>();
            _collider = GetComponent<Collider>();
        }

        private void Start()
        {
            if (_outline == null) _outline = GetComponent<Outline>() ?? gameObject.AddComponent<Outline>();
            _outline.OutlineMode = Outline.Mode.OutlineAll;
            _outline.OutlineWidth = 3;
            _outline.OutlineColor = _outlineColor;
            _outline.enabled = false;
            if (_collider == null) _collider = GetComponent<Collider>();
            _collider.enabled = false;
        }

        public bool IsMatch(string code)
        {
            return InteractableComponentData != null && code != string.Empty && code == InteractableComponentData.ComponentCode;
        }
        
        public void OnPointerDown(PointerEventData eventData)
        {
            if (!HandleToolOperation.Instance._tool || IsTriggered) return;
            HandleToolOperation.Instance._tool.OnTrigger(this);
        }
        
        public void OnObjectSelected()
        {
            _outline.OutlineColor = Color.yellow;
            IsTriggered = true;
            _outline.enabled = RefManager.Instance.FaultManager.Modes == Modes.Easy;
            _collider.enabled = false;
        }
        
        public void OnObjectDeselected()
        {
            _outline.OutlineColor = Color.green;
            _outline.enabled = RefManager.Instance.FaultManager.Modes == Modes.Easy;
            _collider.enabled = true;
        }
        
        public void OnObjectReset()
        {
            _outline.OutlineColor = _outlineColor;
            _outline.enabled = false;
            IsTriggered = false;
            _collider.enabled = false;
        }
    }
}