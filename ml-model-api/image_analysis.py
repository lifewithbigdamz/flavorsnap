import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import base64
import io
import json
from typing import List, Dict, Any, Tuple, Optional, Union
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from scipy import ndimage
from skimage import feature, measure, filters
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
import torch
import torchvision.transforms as transforms

class ImageAnalyzer:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    async def analyze_image(self, image_data: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Perform comprehensive image analysis"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            image_np = np.array(image)
            
            results = {
                "image_info": self._get_image_info(image, image_np),
                "timestamp": time.time(),
                "analysis_type": analysis_type
            }
            
            if analysis_type in ["comprehensive", "quality"]:
                results["quality"] = await self._analyze_quality(image_np)
            
            if analysis_type in ["comprehensive", "composition"]:
                results["composition"] = await self._analyze_composition(image_np)
            
            if analysis_type in ["comprehensive", "color"]:
                results["color"] = await self._analyze_colors(image_np)
            
            if analysis_type in ["comprehensive", "texture"]:
                results["texture"] = await self._analyze_texture(image_np)
            
            if analysis_type in ["comprehensive", "objects"]:
                results["objects"] = await self._detect_objects(image_np)
            
            return results
            
        except Exception as e:
            print(f"Error in image analysis: {e}")
            raise
    
    def _get_image_info(self, image: Image.Image, image_np: np.ndarray) -> Dict[str, Any]:
        """Get basic image information"""
        return {
            "width": image.width,
            "height": image.height,
            "channels": image_np.shape[2] if len(image_np.shape) > 2 else 1,
            "mode": image.mode,
            "format": image.format,
            "size_bytes": len(image.tobytes()),
            "aspect_ratio": image.width / image.height,
            "megapixels": (image.width * image.height) / 1000000
        }
    
    async def _analyze_quality(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image quality metrics"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_quality_sync, image_np
        )
    
    def _analyze_quality_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous quality analysis"""
        # Convert to grayscale if needed
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Sharpness (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Blur detection (FFT based)
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude_spectrum = np.abs(fft_shift)
        blur_score = np.sum(magnitude_spectrum[magnitude_spectrum > np.percentile(magnitude_spectrum, 95)]) / np.sum(magnitude_spectrum)
        
        # Noise estimation
        if len(image_np.shape) == 3:
            noise = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            noise = image_np
        noise_level = np.std(cv2.GaussianBlur(noise, (3, 3), 0) - noise)
        
        # Brightness and contrast
        brightness = np.mean(gray) / 255.0
        contrast = np.std(gray) / 255.0
        
        # Histogram analysis
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_normalized = hist.flatten() / hist.sum()
        
        # Dynamic range
        dynamic_range = np.percentile(gray, 99) - np.percentile(gray, 1)
        
        # Exposure assessment
        overexposed = np.sum(gray > 240) / gray.size
        underexposed = np.sum(gray < 15) / gray.size
        
        # Overall quality score (0-1)
        quality_score = min(laplacian_var / 1000, 1.0) * 0.3 + \
                       (1 - blur_score) * 0.2 + \
                       (1 - noise_level / 50) * 0.2 + \
                       (1 - abs(0.5 - brightness)) * 0.15 + \
                       contrast * 0.15
        
        return {
            "sharpness": float(laplacian_var),
            "blur_score": float(blur_score),
            "noise_level": float(noise_level),
            "brightness": float(brightness),
            "contrast": float(contrast),
            "dynamic_range": float(dynamic_range),
            "overexposed_ratio": float(overexposed),
            "underexposed_ratio": float(underexposed),
            "histogram": hist_normalized.tolist(),
            "quality_score": float(max(0, min(quality_score, 1.0))),
            "recommendations": self._get_quality_recommendations(laplacian_var, blur_score, noise_level, brightness, contrast)
        }
    
    def _get_quality_recommendations(self, sharpness: float, blur: float, noise: float, brightness: float, contrast: float) -> List[str]:
        """Get quality improvement recommendations"""
        recommendations = []
        
        if sharpness < 100:
            recommendations.append("Image appears blurry - consider using a sharper image or applying sharpening")
        
        if blur > 0.7:
            recommendations.append("High blur detected - check focus and camera stability")
        
        if noise > 20:
            recommendations.append("High noise level - consider using lower ISO or apply denoising")
        
        if brightness < 0.2:
            recommendations.append("Image is too dark - increase exposure or brightness")
        elif brightness > 0.8:
            recommendations.append("Image is too bright - decrease exposure or brightness")
        
        if contrast < 0.1:
            recommendations.append("Low contrast - enhance contrast for better visibility")
        
        return recommendations
    
    async def _analyze_composition(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image composition"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_composition_sync, image_np
        )
    
    def _analyze_composition_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous composition analysis"""
        # Convert to grayscale for analysis
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Rule of thirds analysis
        height, width = gray.shape
        third_h, third_w = height // 3, width // 3
        
        # Calculate edge density in each third
        edges = cv2.Canny(gray, 50, 150)
        thirds_density = []
        
        for i in range(3):
            for j in range(3):
                h_start, h_end = i * third_h, (i + 1) * third_h
                w_start, w_end = j * third_w, (j + 1) * third_w
                third_edges = edges[h_start:h_end, w_start:w_end]
                density = np.sum(third_edges > 0) / third_edges.size
                thirds_density.append(density)
        
        # Center of mass
        moments = cv2.moments(gray)
        if moments['m00'] != 0:
            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])
        else:
            cx, cy = width // 2, height // 2
        
        # Symmetry analysis
        left_half = gray[:, :width//2]
        right_half = cv2.flip(gray[:, width//2:], 1)
        if left_half.shape != right_half.shape:
            right_half = cv2.resize(right_half, (left_half.shape[1], left_half.shape[0]))
        symmetry = 1 - np.mean(np.abs(left_half - right_half)) / 255.0
        
        # Horizon line detection
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=width//4, maxLineGap=20)
        horizontal_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if abs(angle) < 30 or abs(angle) > 150:  # Nearly horizontal
                    horizontal_lines.append(line[0])
        
        return {
            "rule_of_thirds_score": float(np.std(thirds_density) * 3),  # Higher variance = better composition
            "thirds_density": [float(d) for d in thirds_density],
            "center_of_mass": [cx, cy],
            "symmetry_score": float(symmetry),
            "horizontal_lines_count": len(horizontal_lines),
            "composition_score": float((np.std(thirds_density) * 3 + symmetry) / 2),
            "recommendations": self._get_composition_recommendations(thirds_density, symmetry)
        }
    
    def _get_composition_recommendations(self, thirds_density: List[float], symmetry: float) -> List[str]:
        """Get composition improvement recommendations"""
        recommendations = []
        
        if np.std(thirds_density) < 0.1:
            recommendations.append("Consider applying rule of thirds - place key elements along the grid lines")
        
        if symmetry > 0.8:
            recommendations.append("High symmetry detected - consider adding asymmetry for more dynamic composition")
        
        return recommendations
    
    async def _analyze_colors(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image colors"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_colors_sync, image_np
        )
    
    def _analyze_colors_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous color analysis"""
        # Convert to different color spaces
        if len(image_np.shape) == 3:
            rgb = image_np
            hsv = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
            lab = cv2.cvtColor(image_np, cv2.COLOR_RGB2LAB)
        else:
            # Convert grayscale to RGB for analysis
            rgb = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
            lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        
        # Dominant colors (K-means clustering)
        pixels = rgb.reshape(-1, 3)
        k = 5  # Number of dominant colors
        
        # Simple color quantization (mock K-means)
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        dominant_colors = []
        for center in kmeans.cluster_centers_:
            dominant_colors.append({
                "rgb": [int(c) for c in center],
                "hex": '#{:02x}{:02x}{:02x}'.format(int(center[0]), int(center[1]), int(center[2]))
            })
        
        # Color statistics
        mean_rgb = np.mean(rgb, axis=(0, 1))
        std_rgb = np.std(rgb, axis=(0, 1))
        
        # Saturation analysis
        saturation = hsv[:, :, 1]
        avg_saturation = np.mean(saturation) / 255.0
        
        # Brightness analysis
        value = hsv[:, :, 2]
        avg_brightness = np.mean(value) / 255.0
        
        # Color temperature estimation
        warm_pixels = np.sum((hsv[:, :, 0] < 30) | (hsv[:, :, 0] > 150))
        cool_pixels = np.sum((hsv[:, :, 0] >= 30) & (hsv[:, :, 0] <= 150))
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        warm_ratio = warm_pixels / total_pixels
        color_temperature = "warm" if warm_ratio > 0.6 else "cool" if warm_ratio < 0.4 else "balanced"
        
        return {
            "dominant_colors": dominant_colors,
            "mean_rgb": [float(c) for c in mean_rgb],
            "std_rgb": [float(c) for c in std_rgb],
            "avg_saturation": float(avg_saturation),
            "avg_brightness": float(avg_brightness),
            "color_temperature": color_temperature,
            "warm_ratio": float(warm_ratio),
            "color_harmony": self._analyze_color_harmony(dominant_colors)
        }
    
    def _analyze_color_harmony(self, colors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze color harmony"""
        if len(colors) < 2:
            return {"harmony_score": 1.0, "harmony_type": "monochromatic"}
        
        # Simple harmony analysis based on color relationships
        harmony_score = 0.0
        harmony_type = "complementary"
        
        # This is a simplified version - in practice, you'd use more sophisticated color theory
        if len(colors) == 2:
            harmony_score = 0.8
            harmony_type = "complementary"
        elif len(colors) == 3:
            harmony_score = 0.7
            harmony_type = "triadic"
        else:
            harmony_score = 0.6
            harmony_type = "analogous"
        
        return {
            "harmony_score": harmony_score,
            "harmony_type": harmony_type
        }
    
    async def _analyze_texture(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Analyze image texture"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._analyze_texture_sync, image_np
        )
    
    def _analyze_texture_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous texture analysis"""
        # Convert to grayscale
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Local Binary Pattern (LBP)
        radius = 3
        n_points = 8 * radius
        lbp = feature.local_binary_pattern(gray, n_points, radius, method='uniform')
        
        # LBP histogram
        lbp_hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
        lbp_hist = lbp_hist.astype(float)
        lbp_hist /= (lbp_hist.sum() + 1e-7)
        
        # GLCM (Gray-Level Co-occurrence Matrix)
        distances = [1]
        angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
        
        try:
            glcm = feature.graycomatrix(gray, distances=distances, angles=angles, levels=256, symmetric=True, normed=True)
            
            # GLCM features
            contrast = feature.graycoprops(glcm, 'contrast').mean()
            dissimilarity = feature.graycoprops(glcm, 'dissimilarity').mean()
            homogeneity = feature.graycoprops(glcm, 'homogeneity').mean()
            energy = feature.graycoprops(glcm, 'energy').mean()
            correlation = feature.graycoprops(glcm, 'correlation').mean()
            
        except:
            # Fallback values if GLCM fails
            contrast = dissimilarity = homogeneity = energy = correlation = 0.5
        
        # Gabor filters
        frequencies = [0.1, 0.3, 0.5]
        thetas = [0, np.pi/4, np.pi/2, 3*np.pi/4]
        
        gabor_responses = []
        for freq in frequencies:
            for theta in thetas:
                real, imag = filters.gabor(gray, frequency=freq, theta=theta)
                gabor_responses.append(np.mean(real))
        
        gabor_mean = np.mean(gabor_responses)
        gabor_std = np.std(gabor_responses)
        
        # Texture classification
        texture_type = self._classify_texture(lbp_hist, contrast, homogeneity, gabor_std)
        
        return {
            "lbp_histogram": lbp_hist.tolist(),
            "glcm_features": {
                "contrast": float(contrast),
                "dissimilarity": float(dissimilarity),
                "homogeneity": float(homogeneity),
                "energy": float(energy),
                "correlation": float(correlation)
            },
            "gabor_features": {
                "mean": float(gabor_mean),
                "std": float(gabor_std)
            },
            "texture_type": texture_type,
            "texture_complexity": float(self._calculate_texture_complexity(lbp_hist))
        }
    
    def _classify_texture(self, lbp_hist: np.ndarray, contrast: float, homogeneity: float, gabor_std: float) -> str:
        """Classify texture type based on features"""
        # Simple rule-based classification
        if homogeneity > 0.8:
            return "smooth"
        elif contrast > 0.5 and gabor_std > 0.3:
            return "rough"
        elif gabor_std > 0.4:
            return "complex"
        else:
            return "medium"
    
    def _calculate_texture_complexity(self, lbp_hist: np.ndarray) -> float:
        """Calculate texture complexity from LBP histogram"""
        # Use entropy as a measure of complexity
        entropy = -np.sum(lbp_hist * np.log2(lbp_hist + 1e-7))
        return float(entropy / 10)  # Normalize to 0-1 range
    
    async def _detect_objects(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Simple object detection using contour analysis"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._detect_objects_sync, image_np
        )
    
    def _detect_objects_sync(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Synchronous simple object detection"""
        # Convert to grayscale
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        min_area = 100
        max_area = gray.shape[0] * gray.shape[1] * 0.5
        
        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate shape properties
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                else:
                    circularity = 0
                
                # Aspect ratio
                aspect_ratio = w / h if h > 0 else 0
                
                objects.append({
                    "bbox": [x, y, w, h],
                    "area": float(area),
                    "perimeter": float(perimeter),
                    "circularity": float(circularity),
                    "aspect_ratio": float(aspect_ratio),
                    "center": [x + w // 2, y + h // 2]
                })
        
        return {
            "objects_detected": len(objects),
            "objects": objects,
            "object_density": float(len(objects) / (gray.shape[0] * gray.shape[1] / 10000))  # Objects per 10k pixels
        }

class ImageEnhancer:
    """Image enhancement utilities"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def enhance_image(self, image_data: str, enhancement_type: str = "auto") -> Dict[str, Any]:
        """Enhance image based on type"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            if enhancement_type == "auto":
                # Analyze and apply appropriate enhancements
                image_np = np.array(image)
                analyzer = ImageAnalyzer()
                analysis = await analyzer._analyze_quality(image_np)
                
                enhanced_image = image.copy()
                
                # Apply enhancements based on analysis
                if analysis["brightness"] < 0.3:
                    enhancer = ImageEnhance.Brightness(enhanced_image)
                    enhanced_image = enhancer.enhance(1.2)
                
                if analysis["contrast"] < 0.3:
                    enhancer = ImageEnhance.Contrast(enhanced_image)
                    enhanced_image = enhancer.enhance(1.3)
                
                if analysis["sharpness"] < 100:
                    enhanced_image = enhanced_image.filter(ImageFilter.SHARPEN)
                
            elif enhancement_type == "brightness":
                enhancer = ImageEnhance.Brightness(image)
                enhanced_image = enhancer.enhance(1.2)
                
            elif enhancement_type == "contrast":
                enhancer = ImageEnhance.Contrast(image)
                enhanced_image = enhancer.enhance(1.3)
                
            elif enhancement_type == "sharpness":
                enhanced_image = image.filter(ImageFilter.SHARPEN)
                
            elif enhancement_type == "color":
                enhancer = ImageEnhance.Color(image)
                enhanced_image = enhancer.enhance(1.1)
                
            else:
                enhanced_image = image
            
            # Convert back to base64
            buffer = io.BytesIO()
            enhanced_image.save(buffer, format='PNG')
            enhanced_data = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "enhanced_image": enhanced_data,
                "enhancement_type": enhancement_type,
                "original_size": [image.width, image.height],
                "enhanced_size": [enhanced_image.width, enhanced_image.height]
            }
            
        except Exception as e:
            print(f"Error in image enhancement: {e}")
            raise

# Utility functions
def create_analyzer() -> ImageAnalyzer:
    """Create image analyzer instance"""
    return ImageAnalyzer()

def create_enhancer() -> ImageEnhancer:
    """Create image enhancer instance"""
    return ImageEnhancer()
