import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Image, 
  Upload, 
  X, 
  Loader2, 
  Eye, 
  Scan, 
  CheckCircle2, 
  AlertCircle,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Download,
  Copy,
  Check,
  Sparkles
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

export interface ImageAnalysisResult {
  description: string;
  objects?: string[];
  text?: string;
  labels?: string[];
  confidence?: number;
}

export interface ImageUpload {
  id: string;
  file: File;
  preview: string;
  status: 'uploading' | 'analyzing' | 'completed' | 'error';
  progress: number;
  result?: ImageAnalysisResult;
  error?: string;
}

interface ImageAnalysisProps {
  onImageSelect?: (file: File) => void;
  onAnalyze?: (imageId: string) => void;
  onRemove?: (imageId: string) => void;
  images?: ImageUpload[];
  maxImages?: number;
  acceptedFormats?: string[];
  maxFileSize?: number; // in MB
}

export function ImageAnalysis({
  onImageSelect,
  onAnalyze,
  onRemove,
  images = [],
  maxImages = 5,
  acceptedFormats = ['.jpg', '.jpeg', '.png', '.webp', '.gif'],
  maxFileSize = 10,
}: ImageAnalysisProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files).filter(file => 
      file.type.startsWith('image/')
    );
    
    files.forEach(file => {
      if (onImageSelect) {
        onImageSelect(file);
      }
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && onImageSelect) {
      Array.from(files).forEach(file => {
        onImageSelect(file);
      });
    }
    e.target.value = '';
  };

  const canAddMore = images.length < maxImages;

  return (
    <div className="space-y-4">
      {/* Upload Zone */}
      {canAddMore && (
        <motion.div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            'relative p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200',
            isDragOver 
              ? 'border-indigo-500 bg-indigo-50/50 scale-[1.02]' 
              : 'border-gray-300 bg-gray-50/50 hover:border-indigo-400 hover:bg-indigo-50/30'
          )}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={acceptedFormats.join(',')}
            className="hidden"
            onChange={handleFileChange}
          />
          
          <div className="text-center">
            <motion.div
              animate={{ y: isDragOver ? -5 : 0 }}
              transition={{ duration: 0.2 }}
              className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-indigo-100 flex items-center justify-center"
            >
              <Image className={cn(
                'w-8 h-8 transition-colors',
                isDragOver ? 'text-indigo-600' : 'text-indigo-400'
              )} />
            </motion.div>
            
            <p className="text-lg font-medium text-gray-900 mb-1">
              {isDragOver ? 'Drop images here' : 'Upload images for analysis'}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Drag & drop or click to browse
            </p>
            
            <div className="flex flex-wrap justify-center gap-2">
              {acceptedFormats.map((format) => (
                <span
                  key={format}
                  className="px-2.5 py-1 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-full"
                >
                  {format}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs text-gray-400">
              Max {maxFileSize}MB per image · Up to {maxImages} images
            </p>
          </div>
        </motion.div>
      )}

      {/* Image Grid */}
      <AnimatePresence>
        {images.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-2 sm:grid-cols-3 gap-4"
          >
            {images.map((image) => (
              <ImageCard
                key={image.id}
                image={image}
                onAnalyze={() => onAnalyze?.(image.id)}
                onRemove={() => onRemove?.(image.id)}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface ImageCardProps {
  image: ImageUpload;
  onAnalyze: () => void;
  onRemove: () => void;
}

function ImageCard({ image, onAnalyze, onRemove }: ImageCardProps) {
  const [isZoomed, setIsZoomed] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopyResult = async () => {
    if (image.result?.description) {
      await navigator.clipboard.writeText(image.result.description);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="relative group"
    >
      <div className={cn(
        'relative rounded-xl overflow-hidden border-2 transition-all duration-200',
        image.status === 'error' 
          ? 'border-red-200' 
          : image.status === 'completed'
          ? 'border-emerald-200'
          : 'border-gray-200'
      )}>
        {/* Image Preview */}
        <div className="relative aspect-square bg-gray-100">
          <img
            src={image.preview}
            alt="Preview"
            className="w-full h-full object-cover transition-transform duration-300"
            style={{ transform: `rotate(${rotation}deg) scale(${isZoomed ? 1.5 : 1})` }}
          />
          
          {/* Overlay Controls */}
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
            <div className="flex gap-2">
              <button
                onClick={() => setIsZoomed(!isZoomed)}
                className="p-2 bg-white/90 hover:bg-white rounded-lg text-gray-700 transition-colors"
                title={isZoomed ? 'Zoom out' : 'Zoom in'}
              >
                {isZoomed ? <ZoomOut className="w-4 h-4" /> : <ZoomIn className="w-4 h-4" />}
              </button>
              <button
                onClick={handleRotate}
                className="p-2 bg-white/90 hover:bg-white rounded-lg text-gray-700 transition-colors"
                title="Rotate"
              >
                <RotateCw className="w-4 h-4" />
              </button>
              <button
                onClick={onRemove}
                className="p-2 bg-red-500/90 hover:bg-red-500 rounded-lg text-white transition-colors"
                title="Remove"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Status Badge */}
          <div className="absolute top-2 left-2">
            <span className={cn(
              'inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium',
              image.status === 'uploading' && 'bg-blue-100 text-blue-700',
              image.status === 'analyzing' && 'bg-amber-100 text-amber-700',
              image.status === 'completed' && 'bg-emerald-100 text-emerald-700',
              image.status === 'error' && 'bg-red-100 text-red-700'
            )}>
              {image.status === 'uploading' && <Loader2 className="w-3 h-3 animate-spin" />}
              {image.status === 'analyzing' && <Scan className="w-3 h-3 animate-pulse" />}
              {image.status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
              {image.status === 'error' && <AlertCircle className="w-3 h-3" />}
              {image.status.charAt(0).toUpperCase() + image.status.slice(1)}
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        {(image.status === 'uploading' || image.status === 'analyzing') && (
          <div className="px-3 py-2 bg-white border-t border-gray-200">
            <div className="flex items-center gap-2">
              <Progress value={image.progress} className="flex-1 h-1.5" />
              <span className="text-xs text-gray-500 w-10 text-right">
                {image.progress}%
              </span>
            </div>
          </div>
        )}

        {/* Error Message */}
        {image.status === 'error' && image.error && (
          <div className="px-3 py-2 bg-red-50 border-t border-red-200">
            <p className="text-xs text-red-600">{image.error}</p>
          </div>
        )}

        {/* Analysis Result */}
        {image.status === 'completed' && image.result && (
          <div className="px-3 py-3 bg-emerald-50 border-t border-emerald-200">
            <div className="flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-700 line-clamp-3">
                  {image.result.description}
                </p>
                
                {/* Detected Objects */}
                {image.result.objects && image.result.objects.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {image.result.objects.map((obj, i) => (
                      <span 
                        key={i}
                        className="px-1.5 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded"
                      >
                        {obj}
                      </span>
                    ))}
                  </div>
                )}

                {/* Extracted Text */}
                {image.result.text && (
                  <div className="mt-2 p-2 bg-white rounded border border-emerald-200">
                    <p className="text-xs text-gray-500 mb-1">Extracted Text:</p>
                    <p className="text-xs text-gray-700 line-clamp-2">{image.result.text}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={handleCopyResult}
                    className="flex items-center gap-1 px-2 py-1 bg-white hover:bg-gray-50 border border-gray-200 rounded text-xs text-gray-600 transition-colors"
                  >
                    {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Analyze Button */}
        {image.status === 'uploading' && image.progress === 100 && (
          <div className="px-3 py-2 bg-white border-t border-gray-200">
            <Button
              onClick={onAnalyze}
              size="sm"
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              <Scan className="w-4 h-4 mr-2" />
              Analyze Image
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Compact image thumbnail for chat messages
interface ImageThumbnailProps {
  src: string;
  alt?: string;
  onClick?: () => void;
  className?: string;
}

export function ImageThumbnail({ src, alt = 'Image', onClick, className }: ImageThumbnailProps) {
  const [isLoaded, setIsLoaded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: isLoaded ? 1 : 0 }}
      className={cn(
        'relative rounded-lg overflow-hidden cursor-pointer group',
        className
      )}
      onClick={onClick}
    >
      <img
        src={src}
        alt={alt}
        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
        onLoad={() => setIsLoaded(true)}
      />
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
        <Eye className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </motion.div>
  );
}

// Image preview modal
interface ImagePreviewModalProps {
  src: string;
  alt?: string;
  isOpen: boolean;
  onClose: () => void;
  analysisResult?: ImageAnalysisResult;
}

export function ImagePreviewModal({ 
  src, 
  alt = 'Image', 
  isOpen, 
  onClose,
  analysisResult 
}: ImagePreviewModalProps) {
  const [rotation, setRotation] = useState(0);
  const [zoom, setZoom] = useState(1);

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div 
        className="relative max-w-5xl max-h-[90vh] w-full flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between p-4 bg-gray-900 rounded-t-lg">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ZoomOut className="w-5 h-5" />
            </button>
            <span className="text-sm text-gray-400">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom(Math.min(3, zoom + 0.25))}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ZoomIn className="w-5 h-5" />
            </button>
            <button
              onClick={() => setRotation((prev) => (prev + 90) % 360)}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              <RotateCw className="w-5 h-5" />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={src}
              download
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              <Download className="w-5 h-5" />
            </a>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Image */}
        <div className="flex-1 bg-gray-800 rounded-b-lg overflow-auto flex items-center justify-center p-4">
          <img
            src={src}
            alt={alt}
            className="max-w-full max-h-[60vh] object-contain transition-transform duration-300"
            style={{ 
              transform: `rotate(${rotation}deg) scale(${zoom})`,
            }}
          />
        </div>

        {/* Analysis Result */}
        {analysisResult && (
          <div className="mt-4 p-4 bg-gray-900 rounded-lg max-h-48 overflow-auto">
            <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              Analysis Result
            </h4>
            <p className="text-sm text-gray-300">{analysisResult.description}</p>
            {analysisResult.objects && (
              <div className="mt-2 flex flex-wrap gap-1">
                {analysisResult.objects.map((obj, i) => (
                  <span key={i} className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
                    {obj}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
