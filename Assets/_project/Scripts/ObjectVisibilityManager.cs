using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ObjectVisibilityManager : MonoBehaviour
{
    [SerializeField] private List<GameObject> targetObjects;
    [SerializeField] private Button toggleButton;
    [SerializeField] private TMP_Text buttonText;
    internal bool objectsVisible = true;

    private void OnEnable()
    {
        toggleButton.onClick.AddListener(ToggleVisibility);
        objectsVisible = true;
        buttonText.text ="Hide Object";
    }

    private void OnDisable()
    {
        toggleButton.onClick.RemoveAllListeners();
    }

    internal void ToggleVisibility()
    {
        objectsVisible = !objectsVisible;
        targetObjects.ForEach(x => x?.SetActive(objectsVisible));
        UpdateButtonText();
    }

    private void UpdateButtonText()
    {
        buttonText.text = $"{(objectsVisible ? "Hide" : "Show")} Object";
    }
}