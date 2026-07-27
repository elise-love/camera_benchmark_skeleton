using com.ipevo.windows.CameraKit;
using com.ipevo.windows.ToolKit;
using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace com.ipevo.windows.demo.WpfApp1
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        private readonly ICCameraStreamProxy.StreamObserver streamObserver;

        public MainWindow()
        {
            InitializeComponent();

            string camerakit_dll_Ver = System.Diagnostics.FileVersionInfo.GetVersionInfo(System.Reflection.Assembly.LoadFrom("CameraKit.dll").Location).FileVersion;
            this.Title = string.Format("IPEVO Document Camera API Demo Code v{0} , CameraKit.dll ({1})", System.Diagnostics.FileVersionInfo.GetVersionInfo(System.Reflection.Assembly.GetExecutingAssembly().Location).FileVersion, camerakit_dll_Ver);

            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceAttached, new NSNotificationCenter.NotificationObserver(this.UpdateDevice));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceDetached, new NSNotificationCenter.NotificationObserver(this.UpdateDevice));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.AutoExposureChanged, new NSNotificationCenter.NotificationObserver(this.CameraAutoExposureStatus));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.ExposureChanged, new NSNotificationCenter.NotificationObserver(this.CameraExposureValue));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.AutoWhitebalanceChanged, new NSNotificationCenter.NotificationObserver(this.CameraAutoWhitebalanceStatus));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.WhitebalanceChanged, new NSNotificationCenter.NotificationObserver(this.CameraWhitebalanceValue));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceZoom, new NSNotificationCenter.NotificationObserver(this.CameraZoomValue));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.FocusChanged, new NSNotificationCenter.NotificationObserver(this.CameraFocusValue));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceFocusBegin, new NSNotificationCenter.NotificationObserver(this.CameraFocusStatus));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceFocusEnd, new NSNotificationCenter.NotificationObserver(this.CameraFocusStatus));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceSingleFocus, new NSNotificationCenter.NotificationObserver(this.CameraFocusMode));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceContinuousFocus, new NSNotificationCenter.NotificationObserver(this.CameraFocusMode));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceSnapshot, new NSNotificationCenter.NotificationObserver(this.DeviceSnapshot));


            this.streamObserver = new ICCameraStreamProxy.StreamObserver(UpdateStream);

            ICCamerasManager.sharedManager.startMonitor();
        }


        private void UpdateDevice(string notificationName, object sender, object userInfo)
        {
            this.Dispatcher.InvokeAsync(new Action(() =>
            {
                switch (notificationName)
                {
                    case ICCamerasManager.ICNotification.DeviceAttached:
                        {
                            if (!this.DevicesComboBox.Items.Contains((userInfo as ICCamera).CameraInstanceName))
                                this.DevicesComboBox.Items.Add((userInfo as ICCamera).CameraInstanceName);
                        }
                        break;
                    case ICCamerasManager.ICNotification.DeviceDetached:
                        {
                            if (this.DevicesComboBox.Items.Contains((userInfo as ICCamera).CameraInstanceName))
                                this.DevicesComboBox.Items.Remove((userInfo as ICCamera).CameraInstanceName);
                        }
                        break;
                    default:
                        break;
                }
            }));
        }

        /// <summary>
        /// Current action device
        /// </summary>
        private ICCamera ActionDevice
        {
            get
            {
                ICCamera camera = null;
                if (this.DevicesComboBox.SelectedItem != null)
                {
                    foreach (ICCamera value in ICCamerasManager.sharedManager.cameras)
                    {
                        if (value.CameraInstanceName == this.DevicesComboBox.SelectedItem.ToString())
                        {
                            camera = value;
                            break;
                        }
                    }
                }
                return camera;
            }
        }

        private ICCamera previousSelectedCamera = null;
        List<Dictionary<ICCamera.FormatKey, object>> supportFormats = new List<Dictionary<ICCamera.FormatKey, object>>();
        private void DevicesComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (this.previousSelectedCamera != null)
                ICCameraStreamProxy.sharedProxy.removeStreamObserver(this.previousSelectedCamera, this.streamObserver);

            if (supportFormats.Count > 0)
                supportFormats.Clear();

            if (e.AddedItems.Count > 0
                && e.AddedItems[0] != null)
            {
                ICCamera camera = this.ActionDevice;
                if (camera != null)
                {
                    // update device info
                    this.supportFormats = camera.supportedFormats();
                    if (this.ResolutionComboBox.Items.Count > 0)
                        this.ResolutionComboBox.Items.Clear();
                    foreach (var value in this.supportFormats)
                        this.ResolutionComboBox.Items.Add(value[ICCamera.FormatKey.FormatInfo]);

                    bool have1080p = false;
                    for (int kk = 0; kk < this.ResolutionComboBox.Items.Count; kk++)
                    {
                        if (this.ResolutionComboBox.Items[kk].ToString().Contains("1920x1080") == true)
                        {
                            this.ResolutionComboBox.SelectedIndex = kk;
                            have1080p = true;
                            break;
                        }
                    }

                    if (have1080p == false)
                    {
                        this.ResolutionComboBox.SelectedIndex = 0;
                    }

                    // initialize user interface
                    this.InitializeUI(camera);

                    this.previousSelectedCamera = camera;
                    ICCameraStreamProxy.sharedProxy.addStreamObserver(camera, this.streamObserver);
                }
            }
            else
            {
                this.previousSelectedCamera = null;
                this.ResolutionComboBox.Items.Clear();
                this.captureWriteableBitmap = null;
                this.DisplayStreamImage.Source = null;
            }
        }

        private void InitializeUI(ICCamera camera)
        {
            short value;
            short delta;
            short maximum;
            short minimum;
            short defaultValue;

            bool isAuto;
            // exposure
            this.AELockCheckBox.IsEnabled = camera.hasCapability(ICCamera.Capability.AutoExposure);
            if (camera.hasCapability(ICCamera.Capability.AutoExposure))
            {
                camera.getAutoExposure(out isAuto);
                this.AELockCheckBox.IsChecked = !isAuto;
            }

            this.ExposureSlider.Visibility = camera.hasCapability(ICCamera.Capability.Exposure) ? Visibility.Visible : Visibility.Collapsed;
            if (camera.hasCapability(ICCamera.Capability.Exposure))
            {
                camera.getExposure(out minimum, ICCamera.PropertyValueType.Minimum);
                camera.getExposure(out maximum, ICCamera.PropertyValueType.Maximum);
                camera.getExposure(out delta, ICCamera.PropertyValueType.Delta);
                camera.getExposure(out defaultValue, ICCamera.PropertyValueType.Default);
                camera.getExposure(out value, ICCamera.PropertyValueType.Current);
                this.ExposureSlider.Minimum = minimum;
                this.ExposureSlider.Maximum = maximum;
                this.ExposureSlider.TickFrequency = delta;
                if (value != defaultValue)
                    this.ExposureSlider.Value = defaultValue;
            }

            // whitebalance
            this.WhiteBalanceSlider.Visibility = camera.hasCapability(ICCamera.Capability.WhiteBalance) ? Visibility.Visible : Visibility.Collapsed;
            if (camera.hasCapability(ICCamera.Capability.WhiteBalance))
            {
                camera.getWhiteBalance(out minimum, ICCamera.PropertyValueType.Minimum);
                camera.getWhiteBalance(out maximum, ICCamera.PropertyValueType.Maximum);
                camera.getWhiteBalance(out delta, ICCamera.PropertyValueType.Delta);
                camera.getWhiteBalance(out _, ICCamera.PropertyValueType.Current);
                this.WhiteBalanceSlider.Minimum = minimum;
                this.WhiteBalanceSlider.Maximum = maximum;
                this.WhiteBalanceSlider.TickFrequency = delta;

                camera.getAutoWhiteBalance(out isAuto);
                if (!isAuto)
                    camera.setAutoWhiteBalance(true);
            }

            // zoom
            this.ZoomSlider.Visibility = camera.hasCapability(ICCamera.Capability.DeviceZoomLevel) ? Visibility.Visible : Visibility.Collapsed;
            if (camera.hasCapability(ICCamera.Capability.DeviceZoomLevel))
            {
                camera.getZoomLevel(out minimum, ICCamera.PropertyValueType.Minimum);
                camera.getZoomLevel(out maximum, ICCamera.PropertyValueType.Maximum);
                camera.getZoomLevel(out delta, ICCamera.PropertyValueType.Delta);
                camera.getZoomLevel(out defaultValue, ICCamera.PropertyValueType.Default);
                camera.getZoomLevel(out value, ICCamera.PropertyValueType.Current);
                this.ZoomSlider.Minimum = minimum;
                this.ZoomSlider.Maximum = maximum;
                this.ZoomSlider.TickFrequency = delta;
                if (value != defaultValue)
                    this.ZoomSlider.Value = defaultValue;
            }

            // focus
            this.FocusSlider.Visibility = camera.hasCapability(ICCamera.Capability.ManualFocus) ? Visibility.Visible : Visibility.Collapsed;
            if (camera.hasCapability(ICCamera.Capability.ManualFocus))
            {
                camera.getFocus(out minimum, ICCamera.PropertyValueType.Minimum);
                camera.getFocus(out maximum, ICCamera.PropertyValueType.Maximum);
                camera.getFocus(out delta, ICCamera.PropertyValueType.Delta);
                camera.getFocus(out _, ICCamera.PropertyValueType.Current);
                this.FocusSlider.Minimum = minimum;
                this.FocusSlider.Maximum = maximum;
                this.FocusSlider.TickFrequency = delta;
            }

            // firmware version
            camera.getFirmwareVersion(out string version);
            this.FirmwareVersionLabel.Content = version;

            // brightness
            camera.getBrightness(out minimum, ICCamera.PropertyValueType.Minimum);
            camera.getBrightness(out maximum, ICCamera.PropertyValueType.Maximum);
            camera.getBrightness(out delta, ICCamera.PropertyValueType.Delta);
            camera.getBrightness(out _, ICCamera.PropertyValueType.Default);
            camera.getBrightness(out value, ICCamera.PropertyValueType.Current);
            this.BrightnessSlider.Minimum = minimum;
            this.BrightnessSlider.Maximum = maximum;
            this.BrightnessSlider.TickFrequency = delta;
            this.BrightnessSlider.Value = value;

            // contrast
            camera.getContrast(out minimum, ICCamera.PropertyValueType.Minimum);
            camera.getContrast(out maximum, ICCamera.PropertyValueType.Maximum);
            camera.getContrast(out delta, ICCamera.PropertyValueType.Delta);
            camera.getContrast(out _, ICCamera.PropertyValueType.Default);
            camera.getContrast(out value, ICCamera.PropertyValueType.Current);
            this.ContrastSlider.Minimum = minimum;
            this.ContrastSlider.Maximum = maximum;
            this.ContrastSlider.TickFrequency = delta;
            this.ContrastSlider.Value = value;

            // gamma
            camera.getGamma(out minimum, ICCamera.PropertyValueType.Minimum);
            camera.getGamma(out maximum, ICCamera.PropertyValueType.Maximum);
            camera.getGamma(out delta, ICCamera.PropertyValueType.Delta);
            camera.getGamma(out _, ICCamera.PropertyValueType.Default);
            camera.getGamma(out value, ICCamera.PropertyValueType.Current);
            this.GammaSlider.Minimum = minimum;
            this.GammaSlider.Maximum = maximum;
            this.GammaSlider.TickFrequency = delta;
            this.GammaSlider.Value = value;

            // hue
            camera.getHue(out minimum, ICCamera.PropertyValueType.Minimum);
            camera.getHue(out maximum, ICCamera.PropertyValueType.Maximum);
            camera.getHue(out delta, ICCamera.PropertyValueType.Delta);
            camera.getHue(out _, ICCamera.PropertyValueType.Default);
            camera.getHue(out value, ICCamera.PropertyValueType.Current);
            this.HueSlider.Minimum = minimum;
            this.HueSlider.Maximum = maximum;
            this.HueSlider.TickFrequency = delta;
            this.HueSlider.Value = value;

            // stauration
            camera.getSaturation(out minimum, ICCamera.PropertyValueType.Minimum);
            camera.getSaturation(out maximum, ICCamera.PropertyValueType.Maximum);
            camera.getSaturation(out delta, ICCamera.PropertyValueType.Delta);
            camera.getSaturation(out _, ICCamera.PropertyValueType.Default);
            camera.getSaturation(out value, ICCamera.PropertyValueType.Current);
            this.Saturationlider.Minimum = minimum;
            this.Saturationlider.Maximum = maximum;
            this.Saturationlider.TickFrequency = delta;
            this.Saturationlider.Value = value;

            // sharpness
            camera.getSharpness(out minimum, ICCamera.PropertyValueType.Minimum);
            camera.getSharpness(out maximum, ICCamera.PropertyValueType.Maximum);
            camera.getSharpness(out delta, ICCamera.PropertyValueType.Delta);
            camera.getSharpness(out _, ICCamera.PropertyValueType.Default);
            camera.getSharpness(out value, ICCamera.PropertyValueType.Current);
            this.SharpnessSlider.Minimum = minimum;
            this.SharpnessSlider.Maximum = maximum;
            this.SharpnessSlider.TickFrequency = delta;
            this.SharpnessSlider.Value = value;
        }

        private void ResolutionComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null
                && this.supportFormats.Count > 0
                && e.AddedItems.Count > 0)
            {
                ICCameraStreamProxy.sharedProxy.stopStreamObserver(camera);
                Dictionary<ICCamera.FormatKey, object> setFormat = this.supportFormats[this.ResolutionComboBox.SelectedIndex];
                camera.setFormat(setFormat);

                ICCameraStreamProxy.sharedProxy.startStreamObserver(camera);
            }
        }

        private void AELockCheckBox_Click(object sender, RoutedEventArgs e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setAutoExposure(!(bool)this.AELockCheckBox.IsChecked);
        }

        private void ExposureSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setExposure((short)e.NewValue);
        }

        private void LedCheckBox_Click(object sender, RoutedEventArgs e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setLight((bool)this.LedCheckBox.IsChecked);
        }

        /// <summary>
        /// camera auto exposure status
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        /// userInfo["AutoExposureStatus"]: type bool
        /// </param>
        private void CameraAutoExposureStatus(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                bool isAuto = Convert.ToBoolean(data[ICCamerasManager.ICCommonString.AutoExposureStatus]);
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera)
                        this.AELockCheckBox.IsChecked = !isAuto;
                }));
            }
        }

        /// <summary>
        /// camera exposure value
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        /// userInfo["ExposureValue"]: type int
        private void CameraExposureValue(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                int exposureValue = Convert.ToInt32(data[ICCamerasManager.ICCommonString.ExposureValue]);
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera)
                        this.ExposureSlider.Value = exposureValue;
                }));
            }
        }

        private void WhiteBalanceLockCheckBox_Click(object sender, RoutedEventArgs e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setAutoWhiteBalance(!(bool)this.WhiteBalanceLockCheckBox.IsChecked);
        }

        private void WhiteBalanceSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null
                && !this.isReceiveCameraWhitebalanceValue)
                camera.setWhiteBalance((short)e.NewValue);
        }

        /// <summary>
        /// camera auto white balance status
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        /// userInfo["AutoWhitebalanceStatus"]: type bool
        private void CameraAutoWhitebalanceStatus(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                bool isAuto = Convert.ToBoolean(data[ICCamerasManager.ICCommonString.AutoWhitebalanceStatus]);
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera)
                        this.WhiteBalanceLockCheckBox.IsChecked = !isAuto;
                }));
            }
        }

        bool isReceiveCameraWhitebalanceValue = false;
        /// <summary>
        /// camera whitebalance value
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        /// userInfo["WhitebalanceValue"]: type int
        private void CameraWhitebalanceValue(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                this.isReceiveCameraWhitebalanceValue = true;
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                int whitebalanceValue = Convert.ToInt32(data[ICCamerasManager.ICCommonString.WhitebalanceValue]);
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera
                        && !(bool)this.WhiteBalanceLockCheckBox.IsChecked)
                        this.WhiteBalanceSlider.Value = whitebalanceValue;
                }));
                this.isReceiveCameraWhitebalanceValue = false;
            }
        }

        private void ZoomSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setZoomLevel((short)e.NewValue);
        }

        /// <summary>
        /// camera zoom level value
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        /// userInfo["ZoomLevel"]: type int
        private void CameraZoomValue(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                int zoomValue = Convert.ToInt32(data[ICCamerasManager.ICCommonString.ZoomLevel]);
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera)
                        this.ZoomSlider.Value = zoomValue;
                }));
            }
        }

        private void FocusButton_Click(object sender, RoutedEventArgs e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
            {
                camera.getAutoFocus(out bool isAuto);
                if (!isAuto)
                    camera.setAutoFocus(true);

                camera.startFocus();
            }
        }



        private void FocusSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null
                && !this.isReceiveCameraFocusValue)
                camera.setFocus((short)e.NewValue);
        }

        bool isReceiveCameraFocusValue = false;
        /// <summary>
        /// camera focus value
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        /// userInfo["FocusValue"]: type int
        private void CameraFocusValue(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                this.isReceiveCameraFocusValue = true;
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                int focusValue = Convert.ToInt32(data[ICCamerasManager.ICCommonString.FocusValue]);
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    this.FocusSlider.Value = focusValue;
                }));
                this.isReceiveCameraFocusValue = false;
            }
        }

        /// <summary>
        /// camera focus status
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        private void CameraFocusStatus(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                string focusStatus = notificationName == ICCamerasManager.ICNotification.DeviceFocusBegin ? "Focus Start" : "Focus Finish";
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera)
                        this.DeviceMessageTextBlock.Text = string.Format("{0} {1}", camera.CameraInstanceName, focusStatus);
                }));
            }
        }

        /// <summary>
        /// camera whitebalance value
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        private void CameraFocusMode(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                string focusMode = notificationName == ICCamerasManager.ICNotification.DeviceSingleFocus ? "AF-S" : "AF-C";
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera)
                        this.DeviceMessageTextBlock.Text = string.Format("{0} {1}", camera.CameraInstanceName, focusMode);
                }));
            }
        }

        private void SnapshotButton_Click(object sender, RoutedEventArgs e)
        {
            this.SaveCameraImage();
        }

        /// <summary>
        /// camera device snapshot
        /// </summary>
        /// <param name="notificationName">notification name</param>
        /// <param name="sender">sender from</param>
        /// <param name="userInfo">
        /// userInfo is hashtable
        /// userInfo["Camera"]: type ICCamera
        private void DeviceSnapshot(string notificationName, object sender, object userInfo)
        {
            if (userInfo != null)
            {
                System.Collections.Hashtable data = userInfo as System.Collections.Hashtable;
                ICCamera camera = data[ICCamerasManager.ICCommonString.Camera] as ICCamera;
                this.Dispatcher.Invoke(new Action(() =>
                {
                    ICCamera selectedCamera = this.ActionDevice;
                    if (camera == selectedCamera)
                        this.SaveCameraImage();
                }));
            }
        }

        private void SaveCameraImage()
        {
            System.Drawing.Bitmap captureBitmap = BitmapSourceToBitmap((BitmapSource)this.captureWriteableBitmap);
            string fileName = AppDomain.CurrentDomain.BaseDirectory + DateTime.Now.ToString("MM-dd-yyyy_HHmmss") + ".jpg";
            captureBitmap.RotateFlip(System.Drawing.RotateFlipType.Rotate180FlipX);
            captureBitmap.Save(fileName);
            captureBitmap?.Dispose();

            //open current folder
            System.Diagnostics.Process.Start(AppDomain.CurrentDomain.BaseDirectory);
        }

        private void BrightnessSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setBrightness((short)e.NewValue);
        }

        private void ContrastSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setContrast((short)e.NewValue);
        }

        private void GammaSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setGamma((short)e.NewValue);
        }

        private void HueSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setHue((short)e.NewValue);
        }

        private void Saturationlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setSaturation((short)e.NewValue);
        }

        private void SharpnessSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
                camera.setSharpness((short)e.NewValue);
        }

        private void ImageAdjustResetButton_Click(object sender, RoutedEventArgs e)
        {
            ICCamera camera = this.ActionDevice;
            if (camera != null)
            {
                camera.getBrightness(out short value, ICCamera.PropertyValueType.Default);
                this.BrightnessSlider.Value = value;

                camera.getContrast(out value, ICCamera.PropertyValueType.Default);
                this.ContrastSlider.Value = value;

                camera.getGamma(out value, ICCamera.PropertyValueType.Default);
                this.GammaSlider.Value = value;

                camera.getHue(out value, ICCamera.PropertyValueType.Default);
                this.HueSlider.Value = value;

                camera.getSaturation(out value, ICCamera.PropertyValueType.Default);
                this.Saturationlider.Value = value;

                camera.getSharpness(out value, ICCamera.PropertyValueType.Default);
                this.SharpnessSlider.Value = value;
            }
        }

        private void UpdateStream(ICCamera camera, IntPtr buffer, int bufferLength, int frameWidth = 0, int frameHeight = 0)
        {
            this.Dispatcher.Invoke(new System.Threading.ThreadStart(() =>
            {
                this.StreamBufferToWriteableBitmap(camera, buffer, bufferLength);
            }));
        }

        [System.Runtime.InteropServices.DllImport("Kernel32.dll", EntryPoint = "RtlMoveMemory")]
        private static extern void CopyMemory(IntPtr Destination, IntPtr Source, int Length);

        readonly object lockObject = new object();
        private void StreamBufferToWriteableBitmap(CameraKit.ICCamera camera, IntPtr buffer, int bufferLength)
        {
            lock (lockObject)
            {
                if (captureWriteableBitmap == null)
                {
                    camera.getFormat(out Dictionary<CameraKit.ICCamera.FormatKey, object> formatInfo);
                    if (formatInfo != null
                        && formatInfo.Count > 0)
                        this.CreateWriteableBitmap(Convert.ToInt32(formatInfo[CameraKit.ICCamera.FormatKey.Width]), Convert.ToInt32(formatInfo[CameraKit.ICCamera.FormatKey.Height]));
                }
                else
                {
                    int writeableBitmapSize = (int)captureWriteableBitmap.Width * (int)captureWriteableBitmap.Height * 4;
                    if (writeableBitmapSize != bufferLength)
                    {
                        captureWriteableBitmap = null;

                        camera.getFormat(out Dictionary<CameraKit.ICCamera.FormatKey, object> formatInfo);
                        if (formatInfo != null
                            && formatInfo.Count > 0)
                            this.CreateWriteableBitmap(Convert.ToInt32(formatInfo[CameraKit.ICCamera.FormatKey.Width]), Convert.ToInt32(formatInfo[CameraKit.ICCamera.FormatKey.Height]));
                    }

                    if (captureWriteableBitmap != null
                        && buffer != IntPtr.Zero)
                    {
                        try
                        {
                            captureWriteableBitmap.Lock();
                            System.Windows.Int32Rect rect = new System.Windows.Int32Rect(0, 0, (int)captureWriteableBitmap.Width, (int)captureWriteableBitmap.Height);
                            IntPtr backbuffer = captureWriteableBitmap.BackBuffer;
                            CopyMemory(backbuffer, buffer, bufferLength);
                            captureWriteableBitmap.AddDirtyRect(rect);
                            captureWriteableBitmap.Unlock();
                        }
                        catch (Exception ex)
                        {
                            System.Diagnostics.Debug.WriteLine(ex.ToString());

                            captureWriteableBitmap = null;
                        }
                    }
                }
            }
        }

        private WriteableBitmap captureWriteableBitmap;
        private void CreateWriteableBitmap(int sourceWidth, int sourceHeight)
        {
            try
            {
                this.captureWriteableBitmap = new WriteableBitmap(sourceWidth, sourceHeight, 96d, 96d, PixelFormats.Bgr32, null);
                this.DisplayStreamImage.Source = this.captureWriteableBitmap;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine(ex.ToString());
            }
        }

        private System.Drawing.Bitmap BitmapSourceToBitmap(BitmapSource bitmapSource)
        {
            if (bitmapSource != null)
            {
                System.Drawing.Bitmap resultBitmap = new System.Drawing.Bitmap(bitmapSource.PixelWidth, bitmapSource.PixelHeight, System.Drawing.Imaging.PixelFormat.Format32bppRgb);
                System.Drawing.Imaging.BitmapData data = resultBitmap.LockBits(new System.Drawing.Rectangle(System.Drawing.Point.Empty, resultBitmap.Size),
                                                                                System.Drawing.Imaging.ImageLockMode.WriteOnly,
                                                                                System.Drawing.Imaging.PixelFormat.Format32bppRgb);
                bitmapSource.CopyPixels(System.Windows.Int32Rect.Empty,
                                        data.Scan0,
                                        data.Height * data.Stride,
                                        data.Stride);
                resultBitmap.UnlockBits(data);
                return resultBitmap;
            }
            return null;
        }

        private void Window_Closed(object sender, EventArgs e)
        {
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.DeviceAttached, new NSNotificationCenter.NotificationObserver(this.UpdateDevice));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.DeviceDetached, new NSNotificationCenter.NotificationObserver(this.UpdateDevice));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.AutoExposureChanged, new NSNotificationCenter.NotificationObserver(this.CameraAutoExposureStatus));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.ExposureChanged, new NSNotificationCenter.NotificationObserver(this.CameraExposureValue));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.AutoWhitebalanceChanged, new NSNotificationCenter.NotificationObserver(this.CameraAutoWhitebalanceStatus));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.WhitebalanceChanged, new NSNotificationCenter.NotificationObserver(this.CameraWhitebalanceValue));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.FocusChanged, new NSNotificationCenter.NotificationObserver(this.CameraFocusValue));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.DeviceFocusBegin, new NSNotificationCenter.NotificationObserver(this.CameraFocusStatus));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.DeviceFocusEnd, new NSNotificationCenter.NotificationObserver(this.CameraFocusStatus));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.DeviceSingleFocus, new NSNotificationCenter.NotificationObserver(this.CameraFocusMode));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.DeviceContinuousFocus, new NSNotificationCenter.NotificationObserver(this.CameraFocusMode));
            NSNotificationCenter.defaultCenter.removeNotificationObserver(ICCamerasManager.ICNotification.DeviceSnapshot, new NSNotificationCenter.NotificationObserver(this.DeviceSnapshot));

            ICCamerasManager.sharedManager.stopMonitor();
        }
    }
}
