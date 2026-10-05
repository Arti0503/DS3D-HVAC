using System;
using System.IO;
using UnityEngine;
using UnityEngine.UI;

namespace CCEPL_CAD
{

    public class ExpiryManager : MonoBehaviour
    {
        [SerializeField] private int expiryDays = 21;
        [SerializeField] private GameObject expiryPopup;
        public Button QuitButton;

        [Serializable]
        private class BuildInfoData
        {
            public string buildDate;
        }

        private void OnEnable()
        {
            QuitButton.onClick.AddListener(QuitApplication);
        }

        private void OnDisable()
        {
            QuitButton.onClick.RemoveAllListeners();
        }

        private void Start()
        {
            #if UNITY_EDITOR
            return;
            #endif
            
            string path = Path.Combine(Application.streamingAssetsPath, "BuildInfo.json");

            if (!File.Exists(path))
            {
                Debug.LogError("BuildInfo.json not found!");
                return;
            }

            string json = File.ReadAllText(path);
            BuildInfoData info = JsonUtility.FromJson<BuildInfoData>(json);

            DateTime buildDate = DateTime.Parse(
                info.buildDate,
                null,
                System.Globalization.DateTimeStyles.RoundtripKind);

            if (DateTime.UtcNow >= buildDate.AddDays(expiryDays))
            {
                if (expiryPopup != null)
                    expiryPopup.SetActive(true);

                Time.timeScale = 0;
            }
        }

        private void QuitApplication()
        {
            Application.Quit();
        }
    }
}