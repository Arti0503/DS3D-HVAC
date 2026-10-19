using System;
using System.Collections;
using System.Collections.Generic;
using CCEPL_CAD.Models;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace CCEPL_CAD
{
    public class HVACCustomizedUI : CustomizedUIBase
    {
        [Header("Slider Configs")]
        [SerializeField] private string[] _speedParameters;
        [SerializeField] private List<AnimationColorChange> _colorParameters;
        [SerializeField] private List<BlendShapeChange> _blendShapeChangeParameters;
        public SliderForSpeed sliderPrefab;
        public GameObject AmplitudeSliderView;
        public GameObject SpeedSliderView;
        public RectTransform container;
        public RectTransform amplitudeContainer;
        public ObjectVisibilityManager ObjectVisibilityManager;

        [Header("Highlights & Idle Visual Controls")]
        public GameObject CompresserHighLightParent;
        public List<GameObject> CompressionHighlightObjects = new List<GameObject>();
        public List<GameObject> ArrowObjects = new List<GameObject>();
        public bool AreCompressionHighlightsActive = true;
        public bool AreArrowsActive = true;
        
        private Coroutine globalDebounceCoroutine;
        private List<SpeedSliderData> speedSliderInstances = new List<SpeedSliderData>();
        private List<ColorSliderData> colorSliderInstances = new List<ColorSliderData>();
        private List<BlendShapeChangeData> blendShapeChangeInstances = new List<BlendShapeChangeData>();

        protected override void Awake()
        {
            base.Awake();
            InitializeVisualReferences();
        }

        protected override void OnEnable()
        {
            base.OnEnable();
            EventManager.RequestToggleCompressionHighlights += SetCompressionHighlightsVisible;
            EventManager.RequestToggleCompressorHighlight += SetIndividualCompressorHighlightVisible;
            EventManager.RequestToggleShowHideObjects += SetShowHideObjects;
            EventManager.RequestToggleArrows += SetArrowsVisible;
            EventManager.RequestToggleSensorHighlight += SetSensorHighlightVisible;
        }

        protected override void OnDisable()
        {
            base.OnDisable();
            EventManager.RequestToggleCompressionHighlights -= SetCompressionHighlightsVisible;
            EventManager.RequestToggleCompressorHighlight -= SetIndividualCompressorHighlightVisible;
            EventManager.RequestToggleShowHideObjects -= SetShowHideObjects;
            EventManager.RequestToggleArrows -= SetArrowsVisible;
            EventManager.RequestToggleSensorHighlight -= SetSensorHighlightVisible;
        }

        private void InitializeVisualReferences()
        {
            if (CompresserHighLightParent == null)
            {
                var t = transform.Find("HVAC_Main/CompresserHighLight");
                if (t == null)
                {
                    var allT = GetComponentsInChildren<Transform>(true);
                    foreach (var child in allT)
                    {
                        if (child.name.IndexOf("Compress", StringComparison.OrdinalIgnoreCase) >= 0 &&
                            child.name.IndexOf("HighLight", StringComparison.OrdinalIgnoreCase) >= 0)
                        {
                            CompresserHighLightParent = child.gameObject;
                            break;
                        }
                    }
                }
                else
                {
                    CompresserHighLightParent = t.gameObject;
                }
            }

            CompressionHighlightObjects.Clear();
            ArrowObjects.Clear();

            if (CompresserHighLightParent != null)
            {
                for (int i = 0; i < CompresserHighLightParent.transform.childCount; i++)
                {
                    var child = CompresserHighLightParent.transform.GetChild(i).gameObject;
                    if (!CompressionHighlightObjects.Contains(child))
                    {
                        CompressionHighlightObjects.Add(child);
                    }
                }
            }

            foreach (var idleObj in IdleObjects)
            {
                if (idleObj == null) continue;
                if (idleObj.name.IndexOf("Compress", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    if (!CompressionHighlightObjects.Contains(idleObj))
                    {
                        CompressionHighlightObjects.Add(idleObj);
                    }
                }
                else
                {
                    if (!ArrowObjects.Contains(idleObj))
                    {
                        ArrowObjects.Add(idleObj);
                    }
                }
            }
        }

        public void SetCompressionHighlightsVisible(bool isVisible)
        {
            AreCompressionHighlightsActive = isVisible;
            if (CompresserHighLightParent != null)
            {
                CompresserHighLightParent.SetActive(isVisible);
            }
            foreach (var obj in CompressionHighlightObjects)
            {
                if (obj != null) obj.SetActive(isVisible);
            }
            EventManager.OnCompressionHighlightsChanged?.Invoke(isVisible);
        }

        public void SetIndividualCompressorHighlightVisible(int compressorIndex, bool isVisible)
        {
            string targetName = "Compression" + compressorIndex;
            string altName = "Compressor" + compressorIndex;
            string altName2 = "Compressor " + compressorIndex;
            string altName3 = "Compresor " + compressorIndex;

            for (int i = 0; i < CompressionHighlightObjects.Count; i++)
            {
                var obj = CompressionHighlightObjects[i];
                if (obj == null) continue;

                if (string.Equals(obj.name, targetName, StringComparison.OrdinalIgnoreCase) ||
                    obj.name.IndexOf(targetName, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    obj.name.IndexOf(altName, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    obj.name.IndexOf(altName2, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    obj.name.IndexOf(altName3, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    obj.name.EndsWith(compressorIndex.ToString()))
                {
                    obj.SetActive(isVisible);
                }
            }

            bool anyChildActive = false;
            for (int i = 0; i < CompressionHighlightObjects.Count; i++)
            {
                var obj = CompressionHighlightObjects[i];
                if (obj != null && obj.activeSelf)
                {
                    anyChildActive = true;
                    break;
                }
            }

            if (CompresserHighLightParent != null)
            {
                CompresserHighLightParent.SetActive(anyChildActive);
            }
            AreCompressionHighlightsActive = anyChildActive;
            EventManager.OnCompressionHighlightsChanged?.Invoke(anyChildActive);
        }

        public void SetShowHideObjects(bool isVisible)
        {
            if (ObjectVisibilityManager != null)
            {
                ObjectVisibilityManager.objectsVisible = isVisible;
                ObjectVisibilityManager.ToggleVisibility();
            }
        }

        public void SetArrowsVisible(bool isVisible)
        {
            AreArrowsActive = isVisible;
            foreach (var obj in ArrowObjects)
            {
                if (obj != null) obj.SetActive(isVisible);
            }
            EventManager.OnArrowsChanged?.Invoke(isVisible);
        }

        private readonly Dictionary<string, GameObject> _cachedSensors = new(StringComparer.OrdinalIgnoreCase);

        public void SetSensorHighlightVisible(string sensorType, bool isVisible)
        {
            if (string.IsNullOrEmpty(sensorType)) return;

            if (!_cachedSensors.TryGetValue(sensorType, out var targetObj) || targetObj == null)
            {
                targetObj = FindSensorObject(sensorType);
                if (targetObj != null)
                {
                    _cachedSensors[sensorType] = targetObj;
                }
            }

            if (targetObj != null)
            {
                var outline = targetObj.GetComponent<Outline>();
                if (outline == null)
                {
                    outline = targetObj.AddComponent<Outline>();
                    outline.OutlineMode = Outline.Mode.OutlineAll;
                    outline.OutlineWidth = 4f;
                }
                outline.OutlineColor = new Color(0.1f, 0.85f, 1f, 1f); // Distinct Cyan highlight
                outline.enabled = isVisible;
                Debug.Log($"[HVACCustomizedUI] Sensor Highlight '{sensorType}' -> {isVisible} on '{targetObj.name}'");
            }
            else
            {
                Debug.LogWarning($"[HVACCustomizedUI] Sensor Highlight '{sensorType}' GameObject not found!");
            }

            EventManager.OnSensorHighlightChanged?.Invoke(sensorType, isVisible);
        }

        private GameObject FindSensorObject(string sensorType)
        {
            string lower = sensorType.ToLowerInvariant();
            var allT = GetComponentsInChildren<Transform>(true);

            foreach (var t in allT)
            {
                string n = t.name.ToLowerInvariant();
                if (lower == "fat" && (n == "fat_sensor" || n.StartsWith("fat_sensor"))) return t.gameObject;
                if (lower == "rat" && (n == "rat_sensor.001" || n == "rat_sensor" || n.StartsWith("rat_sensor"))) return t.gameObject;
                if (lower == "sat" && (n == "sat_sensor" || n.StartsWith("sat_sensor"))) return t.gameObject;
                if (lower == "smoke" && (n == "smoke_detector" || n.StartsWith("smoke_detector"))) return t.gameObject;
            }
            return null;
        }

        protected override void Start()
        {
            base.Start();
            InstantiateSpeedSliders();
            InstantiateColorSliders();
            ResetAnimation();
        }

        public override void TriggerFault(int faultIndex)
        {
            base.TriggerFault(faultIndex);
            if (!ObjectVisibilityManager) return;
            ObjectVisibilityManager.objectsVisible = false;
            ObjectVisibilityManager.ToggleVisibility();
            
            //reset blendshape
            foreach (var bsd in blendShapeChangeInstances)
            {
                bsd.TargetMesh.SetBlendShapeWeight(bsd.BlendShapeIndexs[0], 0);
            }

            AreCompressionHighlightsActive = false;
            AreArrowsActive = false;
            EventManager.OnCompressionHighlightsChanged?.Invoke(false);
            EventManager.OnArrowsChanged?.Invoke(false);
        }

        public override void OnFaultCompleted()
        {
            base.OnFaultCompleted();
            AreCompressionHighlightsActive = true;
            AreArrowsActive = true;
            EventManager.OnCompressionHighlightsChanged?.Invoke(true);
            EventManager.OnArrowsChanged?.Invoke(true);
        }

        public override void ResetAnimation()
        {
            if (!Animator) return;
            if (globalDebounceCoroutine != null) StopCoroutine(globalDebounceCoroutine);

            for (var i = 0; i < Animator.layerCount; i++)
            {
                var currentStateHash = Animator.GetCurrentAnimatorStateInfo(i).fullPathHash;
                Animator.Play(currentStateHash, i, 0f);
            }
            Animator.Update(0f);
            globalDebounceCoroutine = StartCoroutine(ApplyAllSlidersNextFrame());
        }
        
        private IEnumerator ApplyAllSlidersNextFrame()
        {
            yield return null;
            if (!Animator) yield break;

            foreach (var sd in speedSliderInstances)
            {
                if (sd?.SliderComponent == null || string.IsNullOrEmpty(sd.ParameterName)) continue;
                var mapped = GetMappedSliderValue(sd.SliderComponent.value);
                Animator.SetFloat(sd.ParameterName, mapped);
            }

            foreach (var cd in colorSliderInstances)
            {
                if (cd?.SliderComponent == null || cd.TargetMaterial == null) continue;
                var color = Color.Lerp(cd.StartColor, cd.EndColor, cd.SliderComponent.value / 10f);
                cd.TargetMaterial.SetColor("_BaseColor", color);
            }

            foreach (var bsd in blendShapeChangeInstances)
            {
                if(bsd?.SliderComponent == null || bsd.TargetMesh == null || bsd.BlendShapeIndexs == null) continue;
                var value = Mathf.Clamp(bsd.SliderComponent.value, 0f, 10f);
                bsd.TargetMesh.SetBlendShapeWeight(bsd.BlendShapeIndexs[0], value * 10);
            }

            globalDebounceCoroutine = null;
        }

        private void InstantiateSpeedSliders()
        {
            SpeedSliderView?.SetActive(_speedParameters != null && _speedParameters.Length > 0);
            if (_speedParameters == null) return;

            foreach (var param in _speedParameters)
            {
                var newSliderGo = Instantiate(sliderPrefab, container);
                if (!newSliderGo || !newSliderGo.SpeedSlider) continue;
                ConfigureCommonSlider(newSliderGo, param);
                speedSliderInstances.Add(new SpeedSliderData { ParameterName = param, SliderComponent = newSliderGo.SpeedSlider });
            }
        }

        private void InstantiateColorSliders()
        {
            AmplitudeSliderView?.SetActive((_colorParameters != null && _colorParameters.Count > 0) || (_blendShapeChangeParameters != null && _blendShapeChangeParameters.Count > 0));

            foreach (var cd in _colorParameters)
            {
                var newSliderGo = Instantiate(sliderPrefab, amplitudeContainer);
                if (!newSliderGo || !newSliderGo.SpeedSlider) continue;
                ConfigureCommonSlider(newSliderGo, cd.AnimationName);
                var csd = new ColorSliderData
                {
                    TargetMaterial = cd.AnimationMaterial, StartColor = cd.Color1, EndColor = cd.Color2,
                    SliderComponent = newSliderGo.SpeedSlider
                };
                colorSliderInstances.Add(csd);
                newSliderGo.SpeedSlider.onValueChanged.AddListener(v =>
                    cd.AnimationMaterial?.SetColor("_BaseColor", Color.Lerp(csd.StartColor, csd.EndColor, v / 10f)));
            }

            InstantiateBlendShapeSliders();
        }
        
        private void InstantiateBlendShapeSliders()
        {
            foreach (var blendShapeChange in _blendShapeChangeParameters)
            {
                var newSliderGo = Instantiate(sliderPrefab, amplitudeContainer);
                if (!newSliderGo || !newSliderGo.SpeedSlider) continue;
                ConfigureCommonSlider(newSliderGo, blendShapeChange.BlendShapeName);
                var bcd = new BlendShapeChangeData
                {
                    TargetMesh = blendShapeChange.TargetMesh,
                    BlendShapeIndexs = blendShapeChange.BlendShapeIndexs,
                    SliderComponent = newSliderGo.SpeedSlider
                };
                newSliderGo.SpeedSlider.value = 0f;
                blendShapeChangeInstances.Add(bcd);
                // newSliderGo.SpeedSlider.onValueChanged.AddListener(v =>
                //     blendShapeChange.AnimationMaterial?.SetColor("_BaseColor", Color.Lerp(bcd.StartColor, bcd.EndColor, v / 10f)));
            }
        }

        private void ConfigureCommonSlider(SliderForSpeed sliderObj, string displayName)
        {
            var slider = sliderObj.SpeedSlider;
            slider.minValue = 0f; slider.maxValue = 10f; slider.value = 5f;
            if (sliderObj.MinValue != null) sliderObj.MinValue.text = "0";
            if (sliderObj.MaxValue != null) sliderObj.MaxValue.text = "10";
            if (sliderObj.NameText != null) sliderObj.NameText.text = displayName;

            var trigger = sliderObj.SliderEventTrigger;
            bool isInteracting = false;
            Action release = () => { if (isInteracting) { ResetAnimation(); isInteracting = false; } };

            var down = new EventTrigger.Entry { eventID = EventTriggerType.PointerDown };
            down.callback.AddListener(_ => isInteracting = true);
            trigger.triggers.Add(down);

            var drag = new EventTrigger.Entry { eventID = EventTriggerType.EndDrag };
            drag.callback.AddListener(_ => release());
            trigger.triggers.Add(drag);

            var up = new EventTrigger.Entry { eventID = EventTriggerType.PointerUp };
            up.callback.AddListener(_ => release());
            trigger.triggers.Add(up);
        }

        private float GetMappedSliderValue(float raw) => raw <= 5f ? raw / 5f : 1f + (raw - 5f) / 10f;

        protected override void OnReceiveUDPData(List<float> values)
        {
            if (values == null || values.Count == 0) return;
            var valueIndex = 0;

            for (var i = 0; i < speedSliderInstances.Count && valueIndex < values.Count; i++)
            {
                if (!speedSliderInstances[i].SliderComponent) continue;
                speedSliderInstances[i].SliderComponent.value = Mathf.Clamp(values[valueIndex], 0f, 10f);
                valueIndex++;
            }

            for (var i = 0; i < colorSliderInstances.Count && valueIndex < values.Count; i++)
            {
                if (!colorSliderInstances[i].SliderComponent) continue;
                colorSliderInstances[i].SliderComponent.value = Mathf.Clamp(values[valueIndex], 0f, 10f);
                valueIndex++;
            }
            
            for (var i = 0; i < blendShapeChangeInstances.Count && valueIndex < values.Count; i++)
            {
                if (!blendShapeChangeInstances[i].SliderComponent) continue;
                blendShapeChangeInstances[i].SliderComponent.value = Mathf.Clamp(values[valueIndex] / 10, 0f, 10f);
                valueIndex++;
            }

            for (var i = valueIndex; i < values.Count; i++)
            {
                var value = Mathf.FloorToInt(values[i]);

                switch (i - valueIndex)
                {
                    case 0:
                        var visible = value > 0;
                        if (ObjectVisibilityManager)
                        {
                            ObjectVisibilityManager.objectsVisible = visible;
                            ObjectVisibilityManager.ToggleVisibility();
                        }

                        break;

                    case 1:
                        var reverse = value > 0;
                        if (reverse)
#if UNITY_EDITOR
                            UnityEditor.EditorApplication.isPlaying = false;
#else
                            Application.Quit();
#endif
                        break;

                    case 2:
                        var compVisible = value > 0;
                        SetCompressionHighlightsVisible(compVisible);
                        break;
                }
            }

            ResetAnimation();
        }
    }
}