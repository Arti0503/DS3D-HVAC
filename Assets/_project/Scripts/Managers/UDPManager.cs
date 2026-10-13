using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using CCEPL_CAD.Models;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace CCEPL_CAD
{
    public class UDPManager : MonoBehaviour
    {
        [Header("UDP Settings")]
        [SerializeField] private string _remoteIP = "127.0.0.1";
        [SerializeField] private int _listenPort = 5005;
        [SerializeField] private int _remotePort = 5006;
        [SerializeField] private bool _autoUpdateRemoteIPFromSender = true;

        private UdpClient _receiver;
        private UdpClient _sender;
        private Thread _receiveThread;
        private volatile bool _isRunning;

        private readonly ConcurrentQueue<byte[]> _messageQueue = new();
        private readonly object _endpointLock = new();
        private IPEndPoint _remoteEndPoint;
        
        private string _lastReceivedMessage = string.Empty;
        private readonly List<float> _cachedFloatBuffer = new(64);

        #region Unity Lifecycle

        private void Awake()
        {
            Application.runInBackground = true;
        }

        private void OnEnable()
        {
            EventManager.SubmitFault += SubmitFault;
        }

        private void OnDisable()
        {
            EventManager.SubmitFault -= SubmitFault;
        }

        private void Start()
        {
            StartUDP();
        }

        private void Update()
        {
            ProcessMessages();
        }

        private void OnApplicationQuit()
        {
            StopUDP();
        }

        #endregion

        #region UDP Lifecycle

        public void StartUDP()
        {
            if (_isRunning) return;

            try
            {
                _remoteEndPoint = new IPEndPoint(IPAddress.Parse(_remoteIP), _remotePort);

                // Receiver Setup
                _receiver = new UdpClient(_listenPort);
                _receiver.Client.ReceiveTimeout = 1000;

                // Sender Setup
                _sender = new UdpClient();

                _isRunning = true;
                _receiveThread = new Thread(ReceiveLoop)
                {
                    IsBackground = true,
                    Name = "UDP_Receive_Thread"
                };
                _receiveThread.Start();

                Debug.Log($"[UDPManager] Started. Listening: {_listenPort} | Target: {_remoteIP}:{_remotePort}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UDPManager] Start Failed: {ex.Message}");
            }
        }

        public void StopUDP()
        {
            if (!_isRunning) return;

            _isRunning = false;

            try
            {
                _receiver?.Close();
                _sender?.Close();

                if (_receiveThread != null && _receiveThread.IsAlive)
                {
                    _receiveThread.Join(200);
                }

                Debug.Log("[UDPManager] Stopped.");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UDPManager] Stop Error: {ex.Message}");
            }
            finally
            {
                _receiver = null;
                _sender = null;
                _receiveThread = null;
            }
        }

        #endregion

        #region Network Loop & Dispatch

        private void ReceiveLoop()
        {
            IPEndPoint senderEndPoint = new IPEndPoint(IPAddress.Any, 0);

            while (_isRunning)
            {
                try
                {
                    byte[] data = _receiver.Receive(ref senderEndPoint);

                    if (data != null && data.Length > 0)
                    {
                        if (_autoUpdateRemoteIPFromSender && senderEndPoint.Address != null)
                        {
                            lock (_endpointLock)
                            {
                                if (!_remoteEndPoint.Address.Equals(senderEndPoint.Address))
                                {
                                    _remoteEndPoint = new IPEndPoint(senderEndPoint.Address, _remotePort);
                                }
                            }
                        }

                        _messageQueue.Enqueue(data);
                    }
                }
                catch (SocketException)
                {
                    // Expected on socket timeout or close/shutdown
                }
                catch (Exception ex)
                {
                    if (_isRunning)
                    {
                        Debug.LogError($"[UDPManager] Receive Thread Error: {ex.Message}");
                    }
                }
            }
        }

        private void ProcessMessages()
        {
            while (_messageQueue.TryDequeue(out byte[] data))
            {
                DecodePacket(data);
            }
        }

        #endregion

        #region Send

        private void SubmitFault(byte[] data)
        {
            if (data == null || data.Length == 0) return;
            SendString(string.Join(",", data));
        }

        public void SendString(string message)
        {
            if (string.IsNullOrEmpty(message) || _sender == null) return;

            try
            {
                byte[] data = Encoding.ASCII.GetBytes(message);

                lock (_endpointLock)
                {
                    _sender.Send(data, data.Length, _remoteEndPoint);
                }

                Debug.Log($"[UDPManager] SENT -> {message}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UDPManager] Send Failed: {ex.Message}");
            }
        }

        #endregion

        #region Decoding

        private void DecodePacket(byte[] data)
        {
            if (data == null || data.Length == 0) return;

            try
            {
                string message = Encoding.UTF8.GetString(data).Trim();

                if (string.IsNullOrEmpty(message) || message == _lastReceivedMessage)
                    return;

                _lastReceivedMessage = message;
                Debug.Log($"[UDPManager] Received -> {message}");

                if (message[0] == '{' || message[0] == '[')
                {
                    DecodeJsonPacket(message);
                }
                else
                {
                    DecodeCsvPacket(message);
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UDPManager] Decode Error: {ex.Message}");
            }
        }

        private void DecodeJsonPacket(string jsonString)
        {
            try
            {
                EventManager.OnFaultsReceived?.Invoke(jsonString);

                SystemSettings targetSettings = null;
                JObject parsedObject = JObject.Parse(jsonString);

                // Check for Root AnimationConfigData structure (case-insensitive)
                if (parsedObject.TryGetValue("Hvac", StringComparison.OrdinalIgnoreCase, out JToken hvacToken))
                {
                    targetSettings = hvacToken.ToObject<SystemSettings>();
                }
                else if (parsedObject.TryGetValue("Bogie", StringComparison.OrdinalIgnoreCase, out JToken bogieToken))
                {
                    targetSettings = bogieToken.ToObject<SystemSettings>();
                }
                else if (parsedObject.TryGetValue("Door", StringComparison.OrdinalIgnoreCase, out JToken doorToken))
                {
                    targetSettings = doorToken.ToObject<SystemSettings>();
                }
                else
                {
                    // Fallback to direct SystemSettings payload
                    targetSettings = parsedObject.ToObject<SystemSettings>();
                }

                if (targetSettings == null) return;

                _cachedFloatBuffer.Clear();

                ExtractNumericValues(targetSettings.Speed, _cachedFloatBuffer);
                ExtractNumericValues(targetSettings.Amplitude, _cachedFloatBuffer);

                if (targetSettings.Boolean != null)
                {
                    for (int i = 0; i < targetSettings.Boolean.Count; i++)
                    {
                        _cachedFloatBuffer.Add(targetSettings.Boolean[i].Value ? 1.0f : 0.0f);
                    }
                }

                if (_cachedFloatBuffer.Count > 0)
                {
                    // Send out a copy to preserve isolation for event listeners
                    EventManager.ReceivedUDPData?.Invoke(new List<float>(_cachedFloatBuffer));
                    SendString(string.Join(",", _cachedFloatBuffer));
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UDPManager] JSON Parse Error: {ex.Message}");
            }
        }

        private void DecodeCsvPacket(string message)
        {
            _cachedFloatBuffer.Clear();
            var tokens = message.Split(',');

            for (var i = 0; i < tokens.Length; i++)
            {
                if (float.TryParse(tokens[i].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out float val))
                {
                    _cachedFloatBuffer.Add(val);
                }
            }

            if (_cachedFloatBuffer.Count > 0)
            {
                EventManager.ReceivedUDPData?.Invoke(new List<float>(_cachedFloatBuffer));
                SendString(string.Join(",", _cachedFloatBuffer));
            }
        }

        private static void ExtractNumericValues(List<NumericParameter> parameters, List<float> outputList)
        {
            if (parameters == null) return;
            foreach (var t in parameters)
            {
                outputList.Add(t.Value);
            }
        }

        #endregion
    }
}