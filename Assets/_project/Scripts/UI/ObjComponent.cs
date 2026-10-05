using CCEPL_CAD.Models;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace CCEPL_CAD
{
    public class ObjComponent : MonoBehaviour, IPointerClickHandler
    {
        [SerializeField] private Image _componentIcon;
        [SerializeField] private TMP_Text _componentName;
        internal string ToolCode;

        internal void SetComponent(ComponentData data)
        {
            _componentIcon.sprite = data.ComponentIcon;
            _componentName.text = data.ComponentName;
            ToolCode = data.ComponentCode;
        }

        public void OnPointerClick(PointerEventData eventData)
        {

        }
    }
}