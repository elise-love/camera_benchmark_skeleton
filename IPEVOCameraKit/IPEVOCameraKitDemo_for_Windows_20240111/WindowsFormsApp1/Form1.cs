using com.ipevo.windows.CameraKit;
using com.ipevo.windows.ToolKit;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Windows.Forms;


namespace com.ipevo.windows.demo.WindowsFormsApp1
{
    public partial class Form1 : Form
    {
        private readonly ICCameraStreamProxy.StreamObserver streamObserver;

        public Form1()
        {
            InitializeComponent();
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceAttached, new NSNotificationCenter.NotificationObserver(this.UpdateDevice));
            NSNotificationCenter.defaultCenter.addNotificationObserver(ICCamerasManager.ICNotification.DeviceDetached, new NSNotificationCenter.NotificationObserver(this.UpdateDevice));

            this.streamObserver = new ICCameraStreamProxy.StreamObserver(UpdateStream);
            ICCamerasManager.sharedManager.startMonitor();

        }
        private void UpdateDevice(string notificationName, object sender, object userInfo)
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
        }

        private void UpdateStream(ICCamera camera, IntPtr buffer, int bufferLength, int frameWidth = 0, int frameHeight = 0)
        {
            try
            {
                this.BeginInvoke(new Action(() =>
                {
                    this.StreamBufferToWriteableBitmap(camera, buffer, bufferLength);
                }));
            }
            catch (Exception)
            { }
        }

        [System.Runtime.InteropServices.DllImport("Kernel32.dll", EntryPoint = "RtlMoveMemory")]
        private static extern void CopyMemory(IntPtr Destination, IntPtr Source, int Length);

        readonly object lockObject = new object();
        Bitmap captureBitmap;
        byte[] rgbValues;
        private void StreamBufferToWriteableBitmap(com.ipevo.windows.CameraKit.ICCamera camera, IntPtr buffer, int bufferLength)
        {
            lock (lockObject)
            {
                //if (captureWriteableBitmap == null)
                if (captureBitmap == null)
                {
                    camera.getFormat(out Dictionary<com.ipevo.windows.CameraKit.ICCamera.FormatKey, object> formatInfo);
                    if (formatInfo != null
                        && formatInfo.Count > 0)
                    {
                        this.CreateWriteableBitmap(Convert.ToInt32(formatInfo[com.ipevo.windows.CameraKit.ICCamera.FormatKey.Width]), Convert.ToInt32(formatInfo[com.ipevo.windows.CameraKit.ICCamera.FormatKey.Height]));

                    }
                }
                else
                {

                    int writeableBitmapSize = (int)captureBitmap.Width * (int)captureBitmap.Height * 4;
                    if (writeableBitmapSize != bufferLength)
                    {
                        captureBitmap = null;

                        camera.getFormat(out Dictionary<com.ipevo.windows.CameraKit.ICCamera.FormatKey, object> formatInfo);
                        if (formatInfo != null
                            && formatInfo.Count > 0)
                        {
                            this.CreateWriteableBitmap(Convert.ToInt32(formatInfo[com.ipevo.windows.CameraKit.ICCamera.FormatKey.Width]), Convert.ToInt32(formatInfo[com.ipevo.windows.CameraKit.ICCamera.FormatKey.Height]));
                        }
                    }

                    if (captureBitmap != null && buffer != IntPtr.Zero)
                    {

                        try
                        {
                            BitmapData bmData = captureBitmap.LockBits(new Rectangle(0, 0, captureBitmap.Width, captureBitmap.Height), System.Drawing.Imaging.ImageLockMode.ReadWrite, captureBitmap.PixelFormat);
                            IntPtr scan0 = bmData.Scan0;
                            CopyMemory(scan0, buffer, bufferLength);
                            captureBitmap.UnlockBits(bmData);

                            //this.pictureBox1.Refresh();
                            this.pictureBox1.Invalidate();
                        }
                        catch (Exception ex)
                        {
                            System.Diagnostics.Debug.WriteLine(ex.ToString());
                            //captureWriteableBitmap = null;
                        }
                    }

                }
            }
        }

        private void CreateWriteableBitmap(int sourceWidth, int sourceHeight)
        {
            try
            {
                //this.captureWriteableBitmap = new WriteableBitmap(sourceWidth, sourceHeight, 96d, 96d, PixelFormats.Bgr32, null);
                captureBitmap = new Bitmap(sourceWidth, sourceHeight);
                rgbValues = new byte[sourceWidth * sourceHeight * 4];
                //this.DisplayStreamImage.Source = this.captureWriteableBitmap;
                this.pictureBox1.Image = captureBitmap;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine(ex.ToString());
            }
        }

        private ICCamera previousSelectedCamera = null;
        List<Dictionary<ICCamera.FormatKey, object>> supportFormats = new List<Dictionary<ICCamera.FormatKey, object>>();

        private void DevicesComboBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (this.previousSelectedCamera != null)
                ICCameraStreamProxy.sharedProxy.removeStreamObserver(this.previousSelectedCamera, this.streamObserver);

            if (supportFormats.Count > 0)
            {
                supportFormats.Clear();

            }

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
                    if (this.ResolutionComboBox.Items[kk].ToString().Contains("640x480") == true)
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

                ICCameraStreamProxy.sharedProxy.addStreamObserver(camera, this.streamObserver);

                this.previousSelectedCamera = camera;
            }
        }

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

        private void ResolutionComboBox_SelectedIndexChanged(object sender, EventArgs e)
        {

            ICCamera camera = this.ActionDevice;
            if (camera != null
                && this.supportFormats.Count > 0
                //&& e.AddedItems.Count > 0
                )
            {
                ICCameraStreamProxy.sharedProxy.stopStreamObserver(camera);
                Dictionary<ICCamera.FormatKey, object> setFormat = this.supportFormats[this.ResolutionComboBox.SelectedIndex];
                camera.setFormat(setFormat);

                ICCameraStreamProxy.sharedProxy.startStreamObserver(camera);
            }
        }
    }
}
