// ComfyUI-KikoTools - Width Height Selector with Swap Button (DOM widget)
import { app } from "../../scripts/app.js";

// Full preset definitions — kept in sync with presets.py
const PRESET_DIMENSIONS = {
  // SDXL Square
  "1024×1024": [1024, 1024],
  // SDXL Portrait
  "896×1152": [896, 1152],
  "832×1216": [832, 1216],
  "768×1344": [768, 1344],
  "640×1536": [640, 1536],
  "704×1408": [704, 1408],
  "960×1024": [960, 1024],
  "720×1280": [720, 1280],
  // SDXL Landscape
  "1024×960": [1024, 960],
  "1152×896": [1152, 896],
  "1216×832": [1216, 832],
  "1344×768": [1344, 768],
  "1536×640": [1536, 640],
  "1728×576": [1728, 576],
  "1280×720": [1280, 720],
  // FLUX Cinematic
  "1920×1080": [1920, 1080],
  "1280×768": [1280, 768],
  // FLUX Square
  "1536×1536": [1536, 1536],
  // FLUX Portrait
  "768×1280": [768, 1280],
  "1080×1440": [1080, 1440],
  "1152×1728": [1152, 1728],
  // FLUX Classic
  "1440×1080": [1440, 1080],
  // FLUX Photography
  "1728×1152": [1728, 1152],
  // Ultra-Wide Gaming
  "2560×1080": [2560, 1080],
  // Ultra-Wide Cinematic
  "2048×768": [2048, 768],
  // Ultra-Wide Panoramic
  "1792×768": [1792, 768],
  // Ultra-Wide Banner
  "2304×768": [2304, 768],
  "768×2304": [768, 2304],
  // Ultra-Wide Mobile
  "1080×2560": [1080, 2560],
  // Ultra-Wide Vertical
  "768×2048": [768, 2048],
  "768×1792": [768, 1792],
  // Qwen Square
  "1328×1328": [1328, 1328],
  // Qwen Landscape
  "1664×928": [1664, 928],
  "1472×1104": [1472, 1104],
  "1584×1056": [1584, 1056],
  "2080×688": [2080, 688],
  // Qwen Portrait
  "928×1664": [928, 1664],
  "1104×1472": [1104, 1472],
  "1056×1584": [1056, 1584],
  "688×2080": [688, 2080],
};

app.registerExtension({
  name: "comfyassets.WidthHeightSelector",
  async beforeRegisterNodeDef(nodeType, nodeData, _app) {
    if (nodeData.name === "WidthHeightSelector") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        if (onNodeCreated) onNodeCreated.apply(this, []);

        // Helper: extract raw resolution from formatted preset string
        this.extractResolutionFromPreset = function (presetValue) {
          if (presetValue === "custom") return null;
          if (presetValue.includes(" - ")) {
            return presetValue.split(" - ")[0];
          }
          return presetValue;
        };

        // Dynamic preset → width/height update
        const presetWidget = this.widgets.find((w) => w.name === "preset");
        if (presetWidget) {
          const originalCallback = presetWidget.callback;
          presetWidget.callback = function (value, graphcanvas, node, pos, event) {
            if (originalCallback) {
              originalCallback.call(this, value, graphcanvas, node, pos, event);
            }

            const widthWidget = node.widgets.find((w) => w.name === "width");
            const heightWidget = node.widgets.find((w) => w.name === "height");

            if (widthWidget && heightWidget && value !== "custom") {
              const rawResolution = node.extractResolutionFromPreset(value);
              if (rawResolution && PRESET_DIMENSIONS[rawResolution]) {
                const [w, h] = PRESET_DIMENSIONS[rawResolution];
                widthWidget.value = w;
                heightWidget.value = h;

                if (widthWidget.callback) {
                  widthWidget.callback(w, graphcanvas, node, pos, event);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(h, graphcanvas, node, pos, event);
                }
              }
            }
          };
        }

        // Swap dimensions logic
        this.swapDimensions = function () {
          const widthWidget = this.widgets.find((w) => w.name === "width");
          const heightWidget = this.widgets.find((w) => w.name === "height");
          const presetWidget = this.widgets.find((w) => w.name === "preset");

          if (widthWidget && heightWidget && presetWidget) {
            if (presetWidget.value !== "custom") {
              const rawResolution = this.extractResolutionFromPreset(presetWidget.value);
              if (!rawResolution) return;

              let w, h;
              if (rawResolution.includes("×")) {
                [w, h] = rawResolution.split("×").map((v) => parseInt(v));
              } else if (rawResolution.includes("x")) {
                [w, h] = rawResolution.split("x").map((v) => parseInt(v));
              } else {
                return;
              }

              const swappedRawPreset = `${h}×${w}`;
              const availablePresets = presetWidget.options.values || presetWidget.options;
              let swappedFormattedPreset = null;

              for (const option of availablePresets) {
                if (option === "custom") continue;
                const extractedRes = this.extractResolutionFromPreset(option);
                if (extractedRes === swappedRawPreset) {
                  swappedFormattedPreset = option;
                  break;
                }
              }

              if (swappedFormattedPreset) {
                presetWidget.value = swappedFormattedPreset;
                widthWidget.value = h;
                heightWidget.value = w;
                if (presetWidget.callback) {
                  presetWidget.callback(swappedFormattedPreset, app.canvas, this, [0, 0], null);
                }
                if (widthWidget.callback) {
                  widthWidget.callback(widthWidget.value, app.canvas, this, [0, 0], null);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(heightWidget.value, app.canvas, this, [0, 0], null);
                }
              } else {
                presetWidget.value = "custom";
                widthWidget.value = h;
                heightWidget.value = w;
                if (presetWidget.callback) {
                  presetWidget.callback("custom", app.canvas, this, [0, 0], null);
                }
                if (widthWidget.callback) {
                  widthWidget.callback(widthWidget.value, app.canvas, this, [0, 0], null);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(heightWidget.value, app.canvas, this, [0, 0], null);
                }
              }
            } else {
              const tempWidth = widthWidget.value;
              widthWidget.value = heightWidget.value;
              heightWidget.value = tempWidth;

              if (widthWidget.callback) {
                widthWidget.callback(widthWidget.value, app.canvas, this, [0, 0], null);
              }
              if (heightWidget.callback) {
                heightWidget.callback(heightWidget.value, app.canvas, this, [0, 0], null);
              }
            }

            this.graph?.setDirtyCanvas(true, true);
          }
        };

        // Create swap button as DOM widget
        this.createSwapButton();
      };

      // DOM-based swap button widget
      nodeType.prototype.createSwapButton = function () {
        const buttonContainer = document.createElement("div");
        buttonContainer.style.cssText = `
          padding: 4px;
          text-align: center;
        `;

        const swapButton = document.createElement("button");
        swapButton.innerHTML = "⇄ Swap W×H";
        swapButton.style.cssText = `
          background: #4A90E2;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 6px 12px;
          cursor: pointer;
          font-size: 11px;
          font-weight: bold;
          transition: background 0.2s, transform 0.1s, box-shadow 0.2s;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        `;

        swapButton.addEventListener("mouseenter", () => {
          swapButton.style.background = "#5BA0F2";
          swapButton.style.transform = "translateY(-1px)";
          swapButton.style.boxShadow = "0 3px 6px rgba(0,0,0,0.3)";
        });

        swapButton.addEventListener("mouseleave", () => {
          swapButton.style.background = "#4A90E2";
          swapButton.style.transform = "translateY(0)";
          swapButton.style.boxShadow = "0 2px 4px rgba(0,0,0,0.2)";
        });

        swapButton.addEventListener("mousedown", () => {
          swapButton.style.background = "#3A80D2";
          swapButton.style.transform = "translateY(1px)";
          swapButton.style.boxShadow = "0 1px 2px rgba(0,0,0,0.2)";
        });

        swapButton.addEventListener("mouseup", () => {
          swapButton.style.background = "#5BA0F2";
          swapButton.style.transform = "translateY(-1px)";
          swapButton.style.boxShadow = "0 3px 6px rgba(0,0,0,0.3)";
        });

        swapButton.addEventListener("click", () => {
          this.swapDimensions();
        });

        buttonContainer.appendChild(swapButton);
        this.swapButtonWidget = this.addDOMWidget("swap_button", "div", buttonContainer);
      };
    }
  },
});
