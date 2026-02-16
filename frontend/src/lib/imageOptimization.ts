import { api } from './api';

// Image optimization options
interface ImageOptimizationOptions {
  width?: number;
  height?: number;
  quality?: number;
  format?: 'webp' | 'jpeg' | 'png' | 'auto';
  fit?: 'cover' | 'contain' | 'fill' | 'inside' | 'outside';
}

// Generate optimized image URL
export const getOptimizedImageUrl = (
  originalUrl: string,
  options: ImageOptimizationOptions = {}
): string => {
  const { width, height, quality = 80, format = 'auto', fit = 'cover' } = options;

  // If using an external image optimization service (like Cloudinary, Imgix, etc.)
  // Modify the URL accordingly
  if (originalUrl.includes('cloudinary.com')) {
    const transformations = [
      width && `w_${width}`,
      height && `h_${height}`,
      `q_${quality}`,
      `f_${format}`,
      `c_${fit}`,
    ]
      .filter(Boolean)
      .join(',');

    return originalUrl.replace('/upload/', `/upload/${transformations}/`);
  }

  // For internal API optimization
  const params = new URLSearchParams();
  if (width) params.append('w', width.toString());
  if (height) params.append('h', height.toString());
  params.append('q', quality.toString());
  params.append('f', format);
  params.append('fit', fit);

  return `${originalUrl}?${params.toString()}`;
};

// Lazy load image with Intersection Observer
export const lazyLoadImage = (
  imgElement: HTMLImageElement,
  src: string,
  options?: ImageOptimizationOptions
): (() => void) => {
  const optimizedSrc = getOptimizedImageUrl(src, options);

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          imgElement.src = optimizedSrc;
          observer.disconnect();
        }
      });
    },
    {
      rootMargin: '50px',
      threshold: 0.01,
    }
  );

  observer.observe(imgElement);

  // Return cleanup function
  return () => observer.disconnect();
};

// Preload critical images
export const preloadImage = (src: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = src;
  });
};

// Preload multiple images
export const preloadImages = (srcs: string[]): Promise<void[]> => {
  return Promise.all(srcs.map(preloadImage));
};

// Generate blur placeholder (for Next.js-style blur-up effect)
export const generateBlurPlaceholder = async (
  imageUrl: string,
  width: number = 20
): Promise<string> => {
  try {
    // Fetch the image and create a tiny version for blur placeholder
    const response = await fetch(getOptimizedImageUrl(imageUrl, { width, quality: 10 }));
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (error) {
    console.error('Failed to generate blur placeholder:', error);
    return '';
  }
};

// Image upload with compression
interface ImageUploadOptions {
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
  maxSizeMB?: number;
}

export const compressImage = async (
  file: File,
  options: ImageUploadOptions = {}
): Promise<Blob> => {
  const {
    maxWidth = 1920,
    maxHeight = 1080,
    quality = 0.8,
    maxSizeMB = 5,
  } = options;

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.src = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(img.src);

      // Calculate new dimensions
      let { width, height } = img;
      const aspectRatio = width / height;

      if (width > maxWidth) {
        width = maxWidth;
        height = width / aspectRatio;
      }

      if (height > maxHeight) {
        height = maxHeight;
        width = height * aspectRatio;
      }

      // Create canvas
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Failed to get canvas context'));
        return;
      }

      // Draw image
      ctx.drawImage(img, 0, 0, width, height);

      // Convert to blob
      canvas.toBlob(
        (blob) => {
          if (blob) {
            // Check if compression was sufficient
            if (blob.size > maxSizeMB * 1024 * 1024 && quality > 0.3) {
              // Try again with lower quality
              compressImage(file, { ...options, quality: quality - 0.1 })
                .then(resolve)
                .catch(reject);
            } else {
              resolve(blob);
            }
          } else {
            reject(new Error('Failed to create blob'));
          }
        },
        'image/jpeg',
        quality
      );
    };

    img.onerror = () => {
      URL.revokeObjectURL(img.src);
      reject(new Error('Failed to load image'));
    };
  });
};

// Upload image with compression
export const uploadImage = async (
  file: File,
  uploadUrl: string,
  options: ImageUploadOptions & { onProgress?: (progress: number) => void } = {}
): Promise<{ url: string; width: number; height: number }> => {
  const { onProgress, ...compressionOptions } = options;

  // Compress image
  const compressedBlob = await compressImage(file, compressionOptions);

  // Create form data
  const formData = new FormData();
  formData.append('file', compressedBlob, file.name);

  // Upload
  const response = await api.post(uploadUrl, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
};

// Generate srcset for responsive images
export const generateSrcSet = (
  imageUrl: string,
  widths: number[] = [320, 640, 960, 1280, 1920]
): string => {
  return widths
    .map((width) => `${getOptimizedImageUrl(imageUrl, { width })} ${width}w`)
    .join(', ');
};

// Get appropriate image size based on container width
export const getSizes = (breakpoints: Record<string, string> = {}): string => {
  const defaultSizes = {
    sm: '100vw',
    md: '50vw',
    lg: '33vw',
    xl: '25vw',
  };

  const sizes = { ...defaultSizes, ...breakpoints };

  return Object.entries(sizes)
    .map(([breakpoint, size]) => {
      const minWidth = {
        sm: 640,
        md: 768,
        lg: 1024,
        xl: 1280,
        '2xl': 1536,
      }[breakpoint];

      return minWidth ? `(min-width: ${minWidth}px) ${size}` : size;
    })
    .join(', ');
};

// React hook for image loading state
export const useImageLoad = (src: string) => {
  const [isLoaded, setIsLoaded] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    const img = new Image();
    img.src = src;

    img.onload = () => setIsLoaded(true);
    img.onerror = () => setError(new Error(`Failed to load image: ${src}`));

    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);

  return { isLoaded, error };
};

export default {
  getOptimizedImageUrl,
  lazyLoadImage,
  preloadImage,
  preloadImages,
  generateBlurPlaceholder,
  compressImage,
  uploadImage,
  generateSrcSet,
  getSizes,
  useImageLoad,
};
