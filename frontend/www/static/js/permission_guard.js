/**
 * Hamnasheen Native Permission Guard Utility
 * Architected strictly for Capacitor 6 / Android 
 */

const PermissionGuard = (() => {

    // Detect if running inside the native app container
    const isNative = window.Capacitor && window.Capacitor.isNativePlatform();

    // Safe Plugin Extractors
    const getPlugin = (name) => {
        if (window.Capacitor && window.Capacitor.Plugins) {
            return window.Capacitor.Plugins[name];
        }
        return null;
    };

    // 1. The Premium Toast UI
    const showToast = (message, type = 'error', showSettingsBtn = false) => {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `hn-toast ${type}`;
        
        let contentHtml = `
            <div class="toast-content">
                <i class="ti ti-${type === 'error' ? 'alert-circle' : 'circle-check'}"></i>
                <span>${message}</span>
            </div>
        `;

        if (showSettingsBtn) {
            contentHtml += `<button class="toast-action-btn" id="toastSettingsBtn">Settings</button>`;
        }

        toast.innerHTML = contentHtml;

        if (showSettingsBtn) {
            // Delayed listener to ensure button renders in DOM
            setTimeout(() => {
                const btn = toast.querySelector('#toastSettingsBtn');
                if (btn) {
                            btn.onclick = async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log("[PermissionGuard] Triggering Native Settings Redirect...");
                        
                        const App = getPlugin('App');
                        if (App && typeof App.openAppSettings === 'function') {
                            try {
                                await App.openAppSettings();
                            } catch (err) {
                                console.error("App.openAppSettings failed:", err);
                            }
                        } else {
                            alert("Please open Android Settings > Apps > Hamnasheen > Permissions to enable manually.");
                        }
                    };
                }
            }, 50);
        }

        container.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    };

    // 2. Core Interceptor Function
    const intercept = async (requirements, successCallback) => {
        const wantsVideo = !!requirements.video;
        const wantsAudio = !!requirements.audio;

        console.log(`[PermissionGuard] Guarding -> Audio: ${wantsAudio}, Video: ${wantsVideo}`);

        // Fallback for Desktop/Web Browser Testing
        if (!isNative) {
            console.warn("[PermissionGuard] Running on Web. Falling back to browser media stream request.");
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: wantsAudio, video: wantsVideo });
                stream.getTracks().forEach(t => t.stop());
                successCallback();
            } catch (e) {
                showToast("Browser blocked access to Camera/Microphone.", "error", false);
            }
            return;
        }

        // --- NATIVE EXECUTION FLOW ---
        try {
            // Check and Request Microphone (Audio)
            if (wantsAudio) {
                const VoiceRecorder = getPlugin('VoiceRecorder');
                if (!VoiceRecorder) {
                    throw new Error("VoiceRecorder plugin not found. Did you run 'npx cap sync'?");
                }

                // Request Native Audio Permission
                const micPerm = await VoiceRecorder.requestAudioRecordingPermission();
                if (!micPerm || micPerm.value !== true) {
                    throw new Error("MICROPHONE_DENIED");
                }
                console.log("[PermissionGuard] Native Microphone: GRANTED");
            }

            // Check and Request Camera (Video)
            if (wantsVideo) {
                const Camera = getPlugin('Camera');
                if (!Camera) {
                    throw new Error("Camera plugin not found. Did you run 'npx cap sync'?");
                }

                // Request Native Camera System Permission
                const camPerm = await Camera.requestPermissions({ permissions: ['camera'] });
                if (camPerm.camera !== 'granted') {
                    throw new Error("CAMERA_DENIED");
                }
                console.log("[PermissionGuard] Native Camera: GRANTED");
            }

            // All system level requirements met!
            successCallback();

        } catch (err) {
            console.error("[PermissionGuard] Hard Denial Exception:", err.message);

            let friendlyMessage = "Required permissions were denied.";
            if (err.message === "MICROPHONE_DENIED") {
                friendlyMessage = "Microphone permission is strictly required.";
            } else if (err.message === "CAMERA_DENIED") {
                friendlyMessage = "Camera permission is required for video feeds.";
            } else if (err.message.includes("plugin not found")) {
                friendlyMessage = "Device setup incomplete. Rebuild native app.";
            }

            // Triggers the toast with Settings redirect ENABLED
            showToast(friendlyMessage, 'error', true);
        }
    };

    return { intercept, showToast };
})();

// Expose globally for window space execution
window.PermissionGuard = PermissionGuard;
