using System;
using System.Collections;
using System.Collections.Generic;
using CCEPL_CAD.Models;
using UnityEngine;
using UnityEngine.UI;

namespace CCEPL_CAD
{
    public class DirectModelRotatorAndScaler : MonoBehaviour
    {
        [Header("Rotation Settings")] [SerializeField]
        private float rotateSpeedMouse = 0.5f;

        [SerializeField] private float rotateSpeedTouch = 0.15f;

        [Header("Scale/Zoom Settings")] [SerializeField]
        private float mouseScrollSensitivity = 0.1f;

        [SerializeField] private float touchPinchSensitivity = 0.005f;
        [SerializeField] private float minScale = 0.5f;
        [SerializeField] private float maxScale = 3.0f;

        private Vector3 lastMousePosition;
        private float currentScaleFactor;
        private Vector3 initialLocalScale;
        public static bool IsLocked { get; set; } = false;

        private void OnEnable()
        {
            EventManager.OnCameraLockStateChanged += SetLockState;
        }

        private void OnDisable()
        {
            EventManager.OnCameraLockStateChanged -= SetLockState;
        }

        private void SetLockState(bool locked)
        {
            locked = false;
            IsLocked = locked;
        }

        private void Start()
        {
            initialLocalScale = transform.localScale;
            currentScaleFactor = 1.0f;
        }

        private void Update()
        {
            if (IsLocked) return;
            if (Utils.IsPointerOverUI()) return;

            if (Input.touchCount > 0) HandleTouchInput();
            else HandleMouseInput();
        }
        

        private void HandleMouseInput()
        {
            // if (Input.GetMouseButtonDown(0)) lastMousePosition = Input.mousePosition;
            // else if (Input.GetMouseButton(0))
            // {
            //     Vector3 delta = Input.mousePosition - lastMousePosition;
            //     lastMousePosition = Input.mousePosition;
            //
            //     transform.Rotate(Vector3.up, -delta.x * rotateSpeedMouse, Space.World);
            //     transform.Rotate(Vector3.right, delta.y * rotateSpeedMouse, Space.World);
            // }

            float scrollInput = Input.GetAxis("Mouse ScrollWheel");
            if (!(Mathf.Abs(scrollInput) > 0.01f)) return;
            currentScaleFactor += scrollInput * mouseScrollSensitivity;
            ApplyLocalScaleChanges();
        }

        private void HandleTouchInput()
        {
            if (Input.touchCount == 2)
            {
                Touch touch0 = Input.GetTouch(0);
                Touch touch1 = Input.GetTouch(1);

                Vector2 touchZeroPrevPos = touch0.position - touch0.deltaPosition;
                Vector2 touchOnePrevPos = touch1.position - touch1.deltaPosition;

                float prevTouchDeltaMag = (touchZeroPrevPos - touchOnePrevPos).magnitude;
                float touchDeltaMag = (touch0.position - touch1.position).magnitude;

                float deltaMagnitudeDiff = touchDeltaMag - prevTouchDeltaMag;

                currentScaleFactor += deltaMagnitudeDiff * touchPinchSensitivity;
                ApplyLocalScaleChanges();
                
                /*Vector2 averageDelta = (touch0.deltaPosition + touch1.deltaPosition) * 0.5f;
                RotateObject(averageDelta);*/
            }
        }
        
        internal void RotateObject(Vector2 delta)
        {
            transform.Rotate(
                Vector3.up,
                -delta.x * rotateSpeedTouch,
                Space.World);

            transform.Rotate(
                Vector3.right,
                delta.y * rotateSpeedTouch,
                Space.World);
        }

        private void ApplyLocalScaleChanges()
        {
            currentScaleFactor = Mathf.Clamp(currentScaleFactor, minScale, maxScale);
            transform.localScale = initialLocalScale * currentScaleFactor;
        }
    }
}