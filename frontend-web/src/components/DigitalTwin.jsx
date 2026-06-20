import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from "react";

const DigitalTwin = forwardRef(({ warehouseId, token, onLocationSelected, containerStyle }, ref) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const unityInstanceRef = useRef(null);
  const scriptLoadedRef = useRef(false);
  const tokenRef = useRef(token);
  const warehouseIdRef = useRef(warehouseId);
  useEffect(() => { tokenRef.current = token; }, [token]);
  useEffect(() => { warehouseIdRef.current = warehouseId; }, [warehouseId]);

  useImperativeHandle(ref, () => ({
    setProductFilter(productId) {
      if (unityInstanceRef.current) {
        unityInstanceRef.current.SendMessage("WarehouseManager", "SetFilter", JSON.stringify({ type: "product_id", value: productId }));
      }
    },
    clearFilter() {
      unityInstanceRef.current?.SendMessage("WarehouseManager", "SetFilter", JSON.stringify({ type: "all" }));
    },
    enterSelectionMode(filter) {
      unityInstanceRef.current?.SendMessage("WarehouseManager", "EnterLocationSelectionMode", JSON.stringify(filter));
    },
    exitSelectionMode() {
      unityInstanceRef.current?.SendMessage("WarehouseManager", "ExitLocationSelectionMode", "");
    },
    highlightSelection(locationId) {
      unityInstanceRef.current?.SendMessage("WarehouseManager", "SetSelectionHighlight", locationId);
    },
    clearSelectionHighlight(locationId) {
      unityInstanceRef.current?.SendMessage("WarehouseManager", "ClearSelectionHighlight", locationId);
    },
    resetCameraView() {
      unityInstanceRef.current?.SendMessage("WarehouseManager", "ResetCameraView", "");
    },
    reload() {
      if (unityInstanceRef.current) {
        unityInstanceRef.current.SendMessage(
          "WarehouseManager", "Initialize",
          JSON.stringify({ token: tokenRef.current, warehouseId: warehouseIdRef.current })
        );
      }
    },
    requestFullscreen() {
      const canvas = document.getElementById("unity-canvas");
      const elem = canvas?.parentElement || canvas || document.documentElement;
      if (elem.requestFullscreen) elem.requestFullscreen();
      else if (elem.webkitRequestFullscreen) elem.webkitRequestFullscreen();
      else if (elem.mozRequestFullScreen) elem.mozRequestFullScreen();
    },
  }));

  useEffect(() => {
    window.onUnityLocationSelected = (data) => {
      const [locationId, locationLabel] = data.split('|');
      if (onLocationSelected) onLocationSelected(locationId, locationLabel);
    };
    return () => { delete window.onUnityLocationSelected; };
  }, [onLocationSelected]);

useEffect(() => {
  if (scriptLoadedRef.current) return;
  scriptLoadedRef.current = true;

    // Incrementa este número después de cada build de Unity para forzar recarga del navegador
    const UNITY_BUILD = "20260622";
    const buildUrl = "/unity";
    const config = {
      dataUrl:            `${buildUrl}/WebGL.data?v=${UNITY_BUILD}`,
      frameworkUrl:       `${buildUrl}/WebGL.framework.js?v=${UNITY_BUILD}`,
      codeUrl:            `${buildUrl}/WebGL.wasm?v=${UNITY_BUILD}`,
      streamingAssetsUrl: "StreamingAssets",
      companyName:        "DefaultCompany",
      productName:        "unity warehouse",
      productVersion:     "0.1",
    };

    const script = document.createElement("script");
    script.src = `${buildUrl}/WebGL.loader.js?v=${UNITY_BUILD}`;

    script.onload = () => {
      const canvas = document.getElementById("unity-canvas");
      if (!canvas) {
        setError("No se encontró el canvas de Unity.");
        setIsLoading(false);
        return;
      }

      window.createUnityInstance(canvas, config, (progress) => {
        console.log(`Unity cargando: ${Math.round(progress * 100)}%`);
      })
        .then((unityInstance) => {
          unityInstanceRef.current = unityInstance;
          setIsLoading(false);

          unityInstance.SendMessage(
            "WarehouseManager",
            "Initialize",
            JSON.stringify({ token, warehouseId })
          );
        })
        .catch((err) => {
          console.error("Error cargando Unity:", err);
          setError("No se pudo cargar el gemelo digital.");
          setIsLoading(false);
        });
    };

    script.onerror = () => {
      setError("No se encontró el build de Unity.");
      setIsLoading(false);
    };

    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
      if (unityInstanceRef.current) {
        unityInstanceRef.current.Quit();
        unityInstanceRef.current = null;
      }
    };
  }, [warehouseId, token]);

  return (
    <div style={{ position: "relative", width: "100%", height: "500px", borderRadius: "12px", overflow: "hidden", background: "#1a1a2e", ...containerStyle }}>
      <canvas
        id="unity-canvas"
        style={{ width: "100%", height: "100%" }}
      />

      {isLoading && (
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "rgba(26,26,46,0.85)" }}>
          <div style={{ width: "40px", height: "40px", border: "3px solid #185FA5", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite", marginBottom: "12px" }} />
          <p style={{ color: "white", fontSize: "13px" }}>Cargando gemelo digital...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {error && (
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(26,26,46,0.85)" }}>
          <p style={{ color: "#f87171", fontSize: "13px", textAlign: "center", padding: "0 16px" }}>{error}</p>
        </div>
      )}
    </div>
  );
});

export default DigitalTwin;
