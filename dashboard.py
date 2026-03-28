from src.ui import theme_manager, ImageViewer, LoadingUI, SkeletonCard
from src.core import ProgressClassifier
from src.utils.memory_manager import MemoryManager
from src.ui.export_panel import ExportPanel
from src.ui.realtime_preview import RealtimePreview
import panel as pn
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import io
import os
import sys


# Ensure src module is visible
sys.path.append(os.path.abspath(os.path.dirname(__file__)))



# Transforms
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# Save image to correct folder
def save_image(image_obj, predicted_class, image_name="uploaded_image.jpg"):
    save_dir = os.path.join(upload_dir, predicted_class)
    os.makedirs(save_dir, exist_ok=True)
    image_path = os.path.join(save_dir, image_name)
    image_obj.save(image_path)


# Panel UI
image_input = pn.widgets.FileInput(accept='image/*')
output = pn.pane.Markdown("Upload an image of food 🍲")
image_preview = pn.pane.Image(width=300, height=300, visible=False)
processed_preview = pn.pane.Image(width=300, height=300, visible=False)
spinner = pn.indicators.LoadingSpinner(value=False, width=50)

# Create error display components
error_banner = create_error_banner()
error_banner.visible = False

# Create confidence chart component
confidence_chart = create_confidence_chart(animate=True)
confidence_chart_component = confidence_chart.create_layout()

# Preprocessing controls
preprocessing_controls = PreprocessingControls()
preprocessing_panel = preprocessing_controls.create_layout()

# Real-time preview component
realtime_preview = RealtimePreview()
realtime_preview_panel = realtime_preview.create_layout()

# Global variables
original_image = None
processed_image = None

def on_image_update(image):
    """Handle image updates from preprocessing controls."""
    global processed_image
    processed_image = image
    if image:
        processed_preview.object = image
        processed_preview.visible = True

def on_realtime_update(image, preprocessing_params):
    """Handle real-time classification updates."""
    global processed_image
    if image and realtime_preview.realtime_enabled:
        processed_image = image
        realtime_preview.update_image(original_image, image, preprocessing_params)

@handle_user_errors("image upload and processing")
def handle_image_upload():
    """Handle image upload and initialize preprocessing."""
    global original_image, processed_image
    
    if image_input.value is None:
        return
    
    # Validate image file first
    is_valid, validation_error = validate_image_file(image_input.value)
    if not is_valid:
        raise validation_error
    
    # Clear any previous errors
    error_banner.visible = False
    
    # Load the image
    original_image = Image.open(io.BytesIO(image_input.value)).convert('RGB')
    processed_image = original_image.copy()
    
    # Update previews
    image_preview.object = original_image
    image_preview.visible = True
    processed_preview.object = processed_image
    processed_preview.visible = True
    
    # Load image into preprocessing controls
    preprocessing_controls.load_image(original_image)
    preprocessing_controls.on_image_update = on_image_update
    preprocessing_controls.set_realtime_callback(on_realtime_update)
    
    output.object = "📸 Image loaded! Use preprocessing controls to enhance, then classify."

@handle_user_errors("image classification")
def classify(event=None):
    """Classify the uploaded image with preprocessing."""
    global original_image, processed_image
    
    if image_input.value is None:
        output.object = "⚠️ Please upload an image first."
        image_preview.visible = False
        processed_preview.visible = False
        return
    


    # Get preprocessing parameters
    preprocessing_params = preprocessing_controls.get_enhancement_params()
    
    # Check if we have cached results for this image (PWA feature)
    image_hash = hashlib.md5(image_input.value).hexdigest()
    cache_key = f"classification_{image_hash}_{hash(str(preprocessing_params))}"
    
    if pwa_manager and not pwa_manager.is_online:
        # Try to get cached result when offline
        cached_result = pwa_manager.get_cached_api_response(cache_key)
        if cached_result:
            result = cached_result
            output.object = "📱 Using cached classification result (offline mode)"
        else:
            output.object = "📱 No cached result available. Please connect to internet."
            spinner.value = False
            return
    else:
        # Perform classification when online
        result = classifier.classify_image(image_to_classify, preprocessing_params)
        
        # Cache the result for offline use
        if pwa_manager:
            pwa_manager.cache_api_response(cache_key, result, expires_in_hours=24)
    
    # Extract results
    predicted_class = result['predicted_class']
    confidence_score = result['confidence']
    all_probabilities = result['all_probabilities']
    
    # Update confidence chart with all probabilities
    confidence_chart.update_predictions(all_probabilities, predicted_class)


        # Start spinner
        spinner.value = True
        output.object = "🔍 Classifying..."


    except Exception as e:
        output.object = f"❌ Error: {str(e)}"
        spinner.value = False
        confidence_chart.reset()

# Setup image upload handler with error handling
def handle_image_upload_with_error_handling():
    """Wrapper function to handle image upload with error display."""
    try:
        handle_image_upload()
    except UserFriendlyError as e:
        handle_and_display_error(e, "image upload", handle_image_upload_with_error_handling)
    except Exception as e:
        output.object = f"❌ Error: {str(e)}"
        # Reset chart on error
        confidence_chart.reset()
    finally:
        spinner.value = False

def manual_export():
    if current_image and current_predicted_class:
        save_image(current_image, current_predicted_class, image_name="manual_export.jpg")
        output.object = f"💾 Manually exported results for **{current_predicted_class}**"

def export_callback(action, data=None):
    """Callback for export panel operations"""
    if action == 'get_current_data':
        if current_image and current_predicted_class:
            return {
                'image': current_image,
                'predicted_class': current_predicted_class,
                'confidence': current_confidence,
                'timestamp': datetime.now().isoformat()
            }
        return None
    elif action == 'get_batch_data':
        return classification_history.copy()
    elif action == 'export_completed':
        output.object = f"📤 Export completed: {data.get('filepath', 'unknown')}"
    elif action == 'batch_export_completed':
        output.object = f"📤 Batch export completed: {data.get('count', 0)} items exported to {data.get('filepath', 'unknown')}"
    return None

def handle_shortcut(combo):
    global current_image, current_predicted_class
    if combo == 'enter':
        classify()
    elif combo == 'escape':
        ui.clear_image()
        current_image = None
        current_predicted_class = None
    elif combo == 'ctrl+s':
        manual_export()
    elif combo == 'ctrl+h':
        ui.toggle_history()
    elif combo == 'ctrl+d':
        # Toggle dark mode
        if 'dark-theme' in app.css_classes:
            app.css_classes = [c for c in app.css_classes if c != 'dark-theme']
            try:
                pn.config.theme = 'default'
            except:
                pass
        else:
            app.css_classes = app.css_classes + ['dark-theme']
            try:
                pn.config.theme = 'dark'
            except:
                pass

# Export panel setup
export_panel = ExportPanel(on_export_callback=export_callback)

ui = MainInterface(classify_fn=classify, save_image_fn=manual_export)
keyboard_manager = KeyboardManager(handle_shortcut)

# Theme toggle button
theme_toggle = pn.widgets.Button(name='🌙', button_type='light', width=50)
theme_toggle.on_click(lambda event: handle_shortcut('ctrl+d'))

# Header
header = pn.Row(
    pn.pane.Markdown("# 🍽️ FlavorSnap", styles={'margin-top': '0px', 'flex': '1'}),
    theme_toggle,
    sizing_mode='stretch_width',
    css_classes=['header']
)

# Dashboard Layout
dashboard_body = pn.Row(
    ui.get_layout(),
    export_panel.get_panel(),
    sizing_mode='stretch_width'
)

# Setup image upload handler with error handling
image_input.param.watch(lambda event: handle_image_upload_with_error_handling(), 'value')

# Setup classification handler with error handling
def classify_with_error_handling(event):
    """Wrapper function to handle classification with error display."""
    try:
        classify(event)
    except UserFriendlyError as e:
        handle_and_display_error(e, "classification", classify_with_error_handling)
        spinner.value = False
    except Exception as e:
        handle_and_display_error(e, "classification", classify_with_error_handling)
        spinner.value = False
        confidence_chart.reset()

run_button = pn.widgets.Button(name='Classify', button_type='primary')
run_button.on_click(classify_with_error_handling)

# Create PWA status indicator
pwa_status = pn.pane.HTML("""
<div id="pwa-status" style="position: fixed; top: 10px; right: 10px; z-index: 1000;">
    <span id="connection-status" class="online-indicator">🌐 Online</span>
    <button id="pwa-install-button" style="display: none; margin-left: 10px;" class="pwa-install-btn">
        📱 Install App
    </button>
</div>
""")

# Create layout with preprocessing controls and PWA features
upload_section = pn.Column(
    "## 📤 Upload Image",
    image_input,
    pn.layout.Divider(),
)

preview_section = pn.Column(
    "## 🖼️ Image Preview",
    pn.Row(
        pn.Column("### Original", image_preview),
        pn.Column("### Processed", processed_preview),
    ),
)

controls_section = pn.Column(
    "## 🎨 Preprocessing Controls",
    preprocessing_panel,
)

classification_section = pn.Column(
    "## 🍽️ Classification",
    pn.Row(run_button, spinner),
    output,
)

confidence_section = pn.Column(
    "## 📈 Confidence Analysis",
    confidence_chart_component,
)

realtime_section = pn.Column(
    "## 🔄 Real-time Preview",
    realtime_preview_panel,
)

# Main app layout with real-time preview
app = pn.Row(
    pn.Column(
        pwa_status,
        upload_section,
        preview_section,
        error_banner,  # Add error banner to the layout
        classification_section,
        confidence_section,
        realtime_section,
        sizing_mode='stretch_width',
        max_width=900,
    ),
    controls_section,
    sizing_mode='stretch_width',
)

# Add PWA JavaScript to the app
app = pn.Column(
    pn.pane.HTML(pwa_js_template),
    app
)

app.servable()

# Cleanup PWA manager on exit
import atexit
atexit.register(lambda: pwa_manager.close() if pwa_manager else None)
