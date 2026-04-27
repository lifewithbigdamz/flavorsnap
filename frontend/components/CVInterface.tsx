import React, { useState, useRef, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  Camera, 
  Eye, 
  Scissors, 
  Brain, 
  Activity, 
  Play, 
  Square, 
  Download,
  RefreshCw,
  Zap,
  Target,
  Palette,
  Image as ImageIcon
} from 'lucide-react';

interface Detection {
  bbox: number[];
  confidence: number;
  class_id: number;
  class_name: string;
  area: number;
  center: number[];
  color: number[];
  processing_time?: number;
}

interface SegmentationResult {
  mask_data: string;
  segments: Array<{
    class: string;
    pixel_count: number;
    percentage: number;
    bounding_box: number[];
  }>;
  confidence_scores: number[];
  processing_time: number;
  timestamp: string;
}

interface FeatureExtractionResult {
  features: number[];
  feature_vector: number[];
  feature_names: string[];
  processing_time: number;
  timestamp: string;
}

interface QualityAssessmentResult {
  overall_score: number;
  sharpness_score: number;
  brightness_score: number;
  contrast_score: number;
  noise_level: number;
  recommendations: string[];
  processing_time: number;
  timestamp: string;
}

export default function CVInterface() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('detection');
  const [results, setResults] = useState<any>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [maxDetections, setMaxDetections] = useState(100);
  const [processingTime, setProcessingTime] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingResults, setStreamingResults] = useState<Detection[]>([]);

  const handleImageUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setSelectedImage(e.target?.result as string);
        setResults(null);
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const handleCameraCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      const video = document.createElement('video');
      video.srcObject = stream;
      video.play();
      
      // Capture image after 3 seconds
      setTimeout(() => {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(video, 0, 0);
        
        const imageData = canvas.toDataURL('image/jpeg');
        setSelectedImage(imageData);
        setResults(null);
        
        // Stop camera
        stream.getTracks().forEach(track => track.stop());
      }, 3000);
    } catch (error) {
      console.error('Camera access denied:', error);
    }
  }, []);

  const processImage = useCallback(async (processingType: string) => {
    if (!selectedImage) return;

    setIsProcessing(true);
    const startTime = Date.now();

    try {
      let response;
      let endpoint;

      switch (processingType) {
        case 'detection':
          endpoint = '/api/cv/detect';
          response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_data: selectedImage,
              confidence_threshold: confidenceThreshold,
              max_detections: maxDetections
            })
          });
          break;

        case 'segmentation':
          endpoint = '/api/cv/segment';
          response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_data: selectedImage,
              model_type: 'semantic',
              output_format: 'mask'
            })
          });
          break;

        case 'features':
          endpoint = '/api/cv/extract-features';
          response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_data: selectedImage,
              feature_type: 'global',
              normalize: true
            })
          });
          break;

        case 'quality':
          endpoint = '/api/cv/assess-quality';
          response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_data: selectedImage,
              assessment_type: 'comprehensive'
            })
          });
          break;

        default:
          throw new Error('Unknown processing type');
      }

      if (response.ok) {
        const result = await response.json();
        setResults(result);
        setProcessingTime(Date.now() - startTime);
      } else {
        throw new Error('Processing failed');
      }
    } catch (error) {
      console.error('Processing error:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [selectedImage, confidenceThreshold, maxDetections]);

  const startRealTimeProcessing = useCallback(async () => {
    if (!selectedImage) return;

    try {
      const response = await fetch('/api/cv/real-time/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          processing_type: 'detection',
          fps_target: 30,
          quality: 'medium'
        })
      });

      if (response.ok) {
        const session = await response.json();
        setIsStreaming(true);
        console.log('Real-time processing started:', session.session_id);
      }
    } catch (error) {
      console.error('Failed to start real-time processing:', error);
    }
  }, [selectedImage]);

  const stopRealTimeProcessing = useCallback(() => {
    setIsStreaming(false);
    setStreamingResults([]);
  }, []);

  const renderDetectionResults = () => {
    if (!results || !results.detections) return null;

    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Detection Results</h3>
          <Badge variant="outline">
            {results.detections.length} objects detected
          </Badge>
        </div>

        <div className="grid gap-3">
          {results.detections.map((detection: Detection, index: number) => (
            <Card key={index}>
              <CardContent className="p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium">{detection.class_name}</h4>
                    <p className="text-sm text-gray-600">
                      Confidence: {(detection.confidence * 100).toFixed(1)}%
                    </p>
                    <p className="text-sm text-gray-600">
                      Area: {detection.area.toLocaleString()} pixels
                    </p>
                    <p className="text-sm text-gray-600">
                      Position: [{detection.center[0]}, {detection.center[1]}]
                    </p>
                  </div>
                  <div className="text-right">
                    <div 
                      className="w-4 h-4 rounded"
                      style={{
                        backgroundColor: `rgb(${detection.color.join(',')})`
                      }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  };

  const renderSegmentationResults = () => {
    if (!results) return null;

    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Segmentation Results</h3>
          <Badge variant="outline">
            {results.segments?.length || 0} segments
          </Badge>
        </div>

        {results.mask_data && (
          <div className="space-y-3">
            <div className="border rounded-lg p-4">
              <h4 className="font-medium mb-2">Segmentation Mask</h4>
              <img 
                src={`data:image/png;base64,${results.mask_data}`}
                alt="Segmentation mask"
                className="w-full max-w-md mx-auto rounded"
              />
            </div>

            <div className="grid gap-3">
              {results.segments?.map((segment: any, index: number) => (
                <Card key={index}>
                  <CardContent className="p-4">
                    <h4 className="font-medium">{segment.class}</h4>
                    <p className="text-sm text-gray-600">
                      Coverage: {(segment.percentage * 100).toFixed(1)}%
                    </p>
                    <p className="text-sm text-gray-600">
                      Pixels: {segment.pixel_count.toLocaleString()}
                    </p>
                    <Progress 
                      value={segment.percentage * 100} 
                      className="mt-2"
                    />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderFeatureResults = () => {
    if (!results) return null;

    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Feature Extraction Results</h3>
          <Badge variant="outline">
            {results.features?.length || 0} features
          </Badge>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {results.features?.slice(0, 8).map((feature: number, index: number) => (
            <Card key={index}>
              <CardContent className="p-4 text-center">
                <h4 className="font-medium text-sm">{results.feature_names?.[index] || `Feature ${index}`}</h4>
                <p className="text-lg font-bold">{feature.toFixed(4)}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="border rounded-lg p-4">
          <h4 className="font-medium mb-2">Feature Vector Statistics</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Mean:</span>
              <p className="font-medium">
                {(results.feature_vector?.reduce((a: number, b: number) => a + b, 0) / results.feature_vector?.length || 0).toFixed(4)}
              </p>
            </div>
            <div>
              <span className="text-gray-600">Std Dev:</span>
              <p className="font-medium">
                {Math.sqrt(results.feature_vector?.reduce((sq: number, n: number) => sq + Math.pow(n - (results.feature_vector?.reduce((a: number, b: number) => a + b, 0) / results.feature_vector?.length || 0), 2), 0) / results.feature_vector?.length || 0).toFixed(4)}
              </p>
            </div>
            <div>
              <span className="text-gray-600">Min:</span>
              <p className="font-medium">
                {Math.min(...(results.feature_vector || [])).toFixed(4)}
              </p>
            </div>
            <div>
              <span className="text-gray-600">Max:</span>
              <p className="font-medium">
                {Math.max(...(results.feature_vector || [])).toFixed(4)}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderQualityResults = () => {
    if (!results) return null;

    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Quality Assessment</h3>
          <Badge variant={results.overall_score > 0.7 ? "default" : results.overall_score > 0.4 ? "secondary" : "destructive"}>
            Score: {(results.overall_score * 100).toFixed(1)}%
          </Badge>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <h4 className="font-medium text-sm">Sharpness</h4>
              <Progress value={results.sharpness_score * 100} className="mt-2" />
              <p className="text-sm text-gray-600 mt-1">{(results.sharpness_score * 100).toFixed(1)}%</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <h4 className="font-medium text-sm">Brightness</h4>
              <Progress value={results.brightness_score * 100} className="mt-2" />
              <p className="text-sm text-gray-600 mt-1">{(results.brightness_score * 100).toFixed(1)}%</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <h4 className="font-medium text-sm">Contrast</h4>
              <Progress value={results.contrast_score * 100} className="mt-2" />
              <p className="text-sm text-gray-600 mt-1">{(results.contrast_score * 100).toFixed(1)}%</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <h4 className="font-medium text-sm">Noise Level</h4>
              <Progress value={results.noise_level * 100} className="mt-2" />
              <p className="text-sm text-gray-600 mt-1">{(results.noise_level * 100).toFixed(1)}%</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <h4 className="font-medium text-sm">Overall</h4>
              <Progress value={results.overall_score * 100} className="mt-2" />
              <p className="text-sm text-gray-600 mt-1">{(results.overall_score * 100).toFixed(1)}%</p>
            </CardContent>
          </Card>
        </div>

        {results.recommendations && results.recommendations.length > 0 && (
          <div className="border rounded-lg p-4">
            <h4 className="font-medium mb-2">Recommendations</h4>
            <ul className="space-y-1">
              {results.recommendations.map((rec: string, index: number) => (
                <li key={index} className="text-sm text-gray-600">• {rec}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Computer Vision Interface</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
            <Upload className="w-4 h-4 mr-2" />
            Upload Image
          </Button>
          <Button variant="outline" onClick={handleCameraCapture}>
            <Camera className="w-4 h-4 mr-2" />
            Capture Photo
          </Button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleImageUpload}
        className="hidden"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Image Input/Display */}
        <Card>
          <CardHeader>
            <CardTitle>Input Image</CardTitle>
          </CardHeader>
          <CardContent>
            {selectedImage ? (
              <div className="space-y-4">
                <img 
                  src={selectedImage} 
                  alt="Selected" 
                  className="w-full rounded-lg"
                />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setSelectedImage(null)}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Clear
                  </Button>
                  <Button variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                </div>
              </div>
            ) : (
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                <ImageIcon className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600">Upload an image or capture a photo to begin analysis</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Processing Controls */}
        <Card>
          <CardHeader>
            <CardTitle>Processing Controls</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Confidence Threshold: {confidenceThreshold.toFixed(2)}</Label>
              <Slider
                value={[confidenceThreshold]}
                onValueChange={(value) => setConfidenceThreshold(value[0])}
                max={1}
                min={0}
                step={0.05}
                className="mt-2"
              />
            </div>

            <div>
              <Label>Max Detections: {maxDetections}</Label>
              <Slider
                value={[maxDetections]}
                onValueChange={(value) => setMaxDetections(value[0])}
                max={500}
                min={1}
                step={10}
                className="mt-2"
              />
            </div>

            <div className="flex gap-2">
              <Button 
                onClick={() => processImage(activeTab)}
                disabled={!selectedImage || isProcessing}
                className="flex-1"
              >
                {isProcessing ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 mr-2" />
                    Process
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                onClick={isStreaming ? stopRealTimeProcessing : startRealTimeProcessing}
                disabled={!selectedImage}
              >
                {isStreaming ? (
                  <>
                    <Square className="w-4 h-4 mr-2" />
                    Stop
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Real-time
                  </>
                )}
              </Button>
            </div>

            {processingTime > 0 && (
              <div className="text-sm text-gray-600">
                Processing time: {processingTime}ms
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {selectedImage && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="detection">
              <Target className="w-4 h-4 mr-2" />
              Detection
            </TabsTrigger>
            <TabsTrigger value="segmentation">
              <Scissors className="w-4 h-4 mr-2" />
              Segmentation
            </TabsTrigger>
            <TabsTrigger value="features">
              <Brain className="w-4 h-4 mr-2" />
              Features
            </TabsTrigger>
            <TabsTrigger value="quality">
              <Activity className="w-4 h-4 mr-2" />
              Quality
            </TabsTrigger>
          </TabsList>

          <TabsContent value="detection">
            {renderDetectionResults()}
          </TabsContent>

          <TabsContent value="segmentation">
            {renderSegmentationResults()}
          </TabsContent>

          <TabsContent value="features">
            {renderFeatureResults()}
          </TabsContent>

          <TabsContent value="quality">
            {renderQualityResults()}
          </TabsContent>
        </Tabs>
      )}

      {/* Real-time Results */}
      {isStreaming && streamingResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Real-time Detection Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {streamingResults.slice(-5).map((detection, index) => (
                <div key={index} className="flex justify-between items-center p-2 border rounded">
                  <span className="text-sm">{detection.class_name}</span>
                  <Badge variant="outline">
                    {(detection.confidence * 100).toFixed(1)}%
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
