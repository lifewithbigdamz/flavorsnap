from src.ui import theme_manager, ImageViewer, LoadingUI, SkeletonCard
from src.core import ProgressClassifier
from src.utils.memory_manager import MemoryManager
from src.ui.export_panel import ExportPanel
import panel as pn
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import io
import os
import sys
from datetime import datetime

# Ensure src module is visible
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.ui.main_interface import MainInterface
from src.ui.keyboard_manager import KeyboardManager

# Configure Panel Extension and Theme Integration
theme_manager.apply_to_app()
pn.extension(
    css_files=['static/css/image_viewer.css', 'static/css/loading.css'],
    js_files={
        'image_viewer': 'static/js/image_viewer.js',
        'progress_tracker': 'static/js/progress_tracker.js'
    }
)

# Inject JS for shortcuts natively
with open('static/js/keyboard_shortcuts.js', 'r') as f:
    js_code = f.read()

# Custom CSS and the injected script
shortcut_js = pn.pane.HTML(
    f"<style>.keyboard-target {{ display: none !important; }}</style><script>{js_code}</script>",
    width=0, height=0, margin=0, sizing_mode='fixed'
)

# Load model
model_path = 'models/best_model.pth'
class_names = ['Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam']
os.makedirs('models', exist_ok=True)

# Image transform
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

if os.path.exists(model_path):
    model = models.resnet18(weights='IMAGENET1K_V1')
    model.fc = torch.nn.Linear(model.fc.in_features, len(class_names))
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()
else:
    model = None

# Save image function
def save_image(image_obj, predicted_class, image_name="uploaded_image.jpg"):
    save_dir = f"data/train/{predicted_class}"
    os.makedirs(save_dir, exist_ok=True)
    image_path = os.path.join(save_dir, image_name)
    image_obj.save(image_path)
    return image_path

# State variables
current_image = None
current_predicted_class = None
current_confidence = 0.0
classification_history = []

# Interface Setup
def classify(event=None):
    global current_image, current_predicted_class
    if ui.image_input.value is None and current_image is None:
        ui.output.object = "⚠️ Please upload an image first."
        ui.image_preview.visible = False
        return
        
    try:
        if ui.image_input.value is not None:
             image = Image.open(io.BytesIO(ui.image_input.value)).convert('RGB')
             current_image = image
        else:
             image = current_image

        # Update preview
        ui.image_preview.object = image
        ui.image_preview.visible = True

        # Start spinner
        ui.spinner.value = True
        ui.output.object = "🔍 Classifying..."

        if model is None:
            ui.output.object = "❌ Model weights not found. (Dummy run)"
            predicted_class = class_names[0]
            confidence = 0.5
        else:
            # Transform and predict
            img_tensor = transform(image).unsqueeze(0)
            with torch.no_grad():
                outputs = model(img_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
                confidence, pred = torch.max(probabilities, 1)
                predicted_class = class_names[pred.item()]
                confidence = confidence.item()

        current_predicted_class = predicted_class
        current_confidence = confidence
        
        # Save image
        saved_path = save_image(image, predicted_class)
        ui.output.object = f"✅ Identified as **{predicted_class}** ({confidence:.1%} confidence). Image saved!"
        
        # Update export panel with current data
        export_panel.set_current_data(image, predicted_class, confidence)
        
        # Add to history
        history_item = f"- Identified **{predicted_class}** ({confidence:.1%} confidence)"
        current_history = ui.history_panel[1].object
        if current_history == "No history yet.":
            ui.history_panel[1].object = history_item
        else:
            ui.history_panel[1].object = current_history + "\n" + history_item
            
        # Add to classification history for batch export
        classification_history.append({
            'timestamp': datetime.now().isoformat(),
            'predicted_class': predicted_class,
            'confidence': confidence,
            'image': image.copy()
        })
            
    except Exception as e:
        ui.output.object = f"❌ Error: {str(e)}"
    finally:
        ui.spinner.value = False

def manual_export():
    if current_image and current_predicted_class:
        save_image(current_image, current_predicted_class, image_name="manual_export.jpg")
        ui.output.object = f"💾 Manually exported results for **{current_predicted_class}**"

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
        ui.output.object = f"📤 Export completed: {data.get('filepath', 'unknown')}"
    elif action == 'batch_export_completed':
        ui.output.object = f"📤 Batch export completed: {data.get('count', 0)} items exported to {data.get('filepath', 'unknown')}"
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

app = pn.Column(
    shortcut_js,
    keyboard_manager.get_widget(),
    css_classes=[]
)

# App Assembly
app = pn.Column(
    header,
    pn.layout.Divider(),
    dashboard_body,
    sizing_mode='stretch_width'
)

app.servable()
