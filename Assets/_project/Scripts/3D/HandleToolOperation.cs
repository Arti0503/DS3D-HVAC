using System;
using CCEPL_CAD.Models;
using UnityEngine;
using UnityEngine.EventSystems;

namespace CCEPL_CAD
{
    public class HandleToolOperation : MonoBehaviour
    {
        public static HandleToolOperation Instance;
        internal ToolObject _tool;
        Camera _camera;
        [SerializeField] private float distanceFromCamera = 5f;
        [SerializeField] private LayerMask targetLayerMask = ~0; // All layers by default

        private void Awake()
        {
            Instance = this;
        }

        private void OnEnable()
        {
            _camera = Camera.main;
            EventManager.OnToolSelected += ToolSelect;
        }

        private void OnDisable()
        {
            EventManager.OnToolSelected -= ToolSelect;
        }

        private void Update()
        {
            if (_camera == null) _camera = Camera.main;

            // Cross-platform UI obstruction check (Works for Touch and Mouse)
            if (RepairInputHandler.IsPointerOverUI())
            {
                return;
            }

            // Smooth tool position following pointer (Mobile Touch or Desktop Mouse)
            if (_tool && !_tool.IsEngage && _camera != null)
            {
                MoveToolWithPointer();

                // Direct tap/click 3D raycast selection (for touch screens and mobile devices)
                if (RepairInputHandler.IsPointerDown())
                {
                    TryRaycastTarget();
                }
            }
        }

        private void MoveToolWithPointer()
        {
            Vector3 pointerPos = RepairInputHandler.GetPointerPosition();
            Ray ray = _camera.ScreenPointToRay(pointerPos);
            Vector3 targetPosition = ray.GetPoint(distanceFromCamera);

            _tool.transform.position = targetPosition;
        }

        private void TryRaycastTarget()
        {
            Ray ray = RepairInputHandler.GetPointerRay(_camera);
            if (!Physics.Raycast(ray, out RaycastHit hit, 100f, targetLayerMask)) return;
            // var repairTarget = hit.collider.GetComponentInParent<RepairTarget>();
            // if (repairTarget != null)
            // {
            //     repairTarget.TriggerInteraction();
            // }
            // else
            // {
            var componentPart = hit.collider.GetComponentInParent<IntrectableComponentPart>();
            if (componentPart != null && _tool != null)
            {
                _tool.OnTrigger(componentPart);
            }
            //     else if (RepairWorkflowManager.Instance != null)
            //     {
            //         RepairWorkflowManager.Instance.OnGameObjectInteracted(hit.collider.gameObject);
            //     }
            // }
        }

        private void ToolSelect(ToolType tool, ToolObject toolObject)
        {
            if (_tool) Destroy(_tool.gameObject);

            _tool = Instantiate(toolObject ?? RefManager.Instance.ToolObject, transform);
            _tool.Init(tool);
            RefManager.Instance.UIManager._selectedTool = _tool;
        }
    }
}