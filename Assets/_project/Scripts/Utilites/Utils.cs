using UnityEngine;
using System;
    using System.Collections.Generic;
    using System.Text.RegularExpressions;
    using UnityEngine.EventSystems;

    namespace CCEPL_CAD
{ 
    public static class ByteConverter
    {
        public static byte[] ConvertListToBytes(List<int> list)
        {
            byte[] bytes =
                new byte[list.Count * sizeof(int)];

            Buffer.BlockCopy(
                list.ToArray(),
                0,
                bytes,
                0,
                bytes.Length);

            return bytes;
        }

        public static int[] ConvertBytesToInts(byte[] bytes)
        {
            int[] result =
                new int[bytes.Length / sizeof(int)];

            Buffer.BlockCopy(
                bytes,
                0,
                result,
                0,
                bytes.Length);

            return result;
        }
        
        public static float SliderToSpeed(float sliderValue)
        {
            return Mathf.Lerp(1f, 2f, (sliderValue - 1f) / 9f);
        }
        
        public static string SplitWords(string input)
        {
            return Regex.Replace(
                input,
                @"(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])",
                " ");
        }
    }

    public static class Utils
    {
        public static bool IsPointerOverUI()
        {
            if (!EventSystem.current)
                return false;

            if (Input.touchCount <= 0) return EventSystem.current.IsPointerOverGameObject();
            for (var i = 0; i < Input.touchCount; i++)
            {
                if (EventSystem.current.IsPointerOverGameObject(Input.GetTouch(i).fingerId))
                    return true;
            }

            return EventSystem.current.IsPointerOverGameObject();
        }
        
        public static bool HasParameter(Animator animator, string parameterName)
        {
            foreach (var param in animator.parameters)
            {
                if (param.name == parameterName)
                    return true;
            }
            return false;
        }
    }
}