using System;
using System.Collections.Generic;
using CCEPL_CAD.Models;

namespace CCEPL_CAD
{
    public static class EventManager
    {
        public static Action StartApplication;
        public static Action<string> OnFaultsReceived;
        public static Action<ToolType, ToolObject> OnToolSelected;
        public static Action OnWrongToolSelected;
        public static Action<int> OnFaultClick;
        public static Action<Faults> OnFaultDetect;

        public static Action OnStepComplete;
        public static Action OnFaultCompleted;
        public static Action<byte[]> SubmitFault;

        public static Action<List<float>> ReceivedUDPData;
        public static Action ResetAnimation;
        public static Action<bool> OnCameraLockStateChanged;
        public static Action<UnityEngine.Vector3, UnityEngine.Vector3, float> MoveCameraToTransform;

        public static Action<ToolObject> Spawn3DToolObject;
        
        public static Action<string, bool> OnLogMessage;
        public static Action<string> TriggerDisplayText;
    }
}