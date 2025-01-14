import os
import cv2
import numpy as np
import  imagehash
from PIL import Image
from skimage.metrics import structural_similarity
from  concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import eel
from tkinter import filedialog
import tkinter as tk
import cProfile
import io
import pstats
import time
from functools  import lru_cache
from collections import defaultdict
import shutil
import psutil

eel.init('src')

class ImageComparator:
    def __init__(self, max_workersh=4, debug=True):
        self.debuge = debug 
        self.supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
        self.weights = {
            'histogram': 0.6,
            'phash': 0.7,
            'ssim': 0.8,
            'mse': 0.5,
            'hog': 0.7,
            'fourier': 0.5,
            'sift': 0.8
        }
        # Initialize caches and detectors
        self.lock = threading.Lock()
        self.matches = []
        self.image_cache = {}
        self.sift_cache = {}
        self.hog_cache = {}
        self.fourier_cache = {}
        self.phash_cache = {}
        
        # Configure processors
        self.max_workers = os.cpu_count() or 4  # Optimize thread count
        # Massively optimized SIFT
        self.sift = cv2.SIFT_create(
            nfeatures=5000,          # Maximum features
            nOctaveLayers=8,         # Optimal for detail
            contrastThreshold=0.01,  # Detect subtle features
            edgeThreshold=15,        # Balance edge detection
            sigma=1.6               
        )
        # FLANN matcher for faster matching
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
        
        # Set parameters
        self.target_size = (800, 800)
        self.hog_size = (128, 128)
        self.max_cache_size = 100
        self.batch_size = 32  # Increased batch size
        self.comparison_threshold = 0.8
        self.high_similarity_threshold = 0.9
        self.start_time = None
        self.last_update = None
        self.update_interval = 0.25  # 250ms
        self.total_comparisons = 0
        self.completed_comparisons = 0
        self.avg_time_per_comparison = 0
        self.start_time = None
        self.quick_size = (400, 400)  # Smaller size for initial check
        self.memory_threshold = 0.8  # 80% memory threshold

    def standardize_image(self, img):
        if img is None:
            return None
        
        h, w = img.shape[:2]
        aspect = w/h
        
        # Resize preserving aspect ratio
        if aspect > 1:
            new_w = self.target_size[0]
            new_h = int(new_w/aspect)
        else:
            new_h = self.target_size[1]
            new_w = int(new_h*aspect)
        
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Create padded square
        square = np.zeros((self.target_size[0], self.target_size[1], 3), dtype=np.uint8)
        y_offset = (self.target_size[0] - new_h) // 2
        x_offset = (self.target_size[1] - new_w) // 2
        square[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return square

    @lru_cache(maxsize=1000)
    def load_and_prepare_image(self, image_path):
        if image_path in self.image_cache:
            return self.image_cache[image_path]

        try:
            if image_path.lower().endswith(('.bmp', '.gif')):
                pil_img = Image.open(image_path)
                if image_path.lower().endswith('.gif'):
                    pil_img.seek(0)
                img = np.array(pil_img.convert('RGB'))
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                img = cv2.imread(image_path, cv2.IMREAD_COLOR)

            if img is None:
                return None

            # Standardize image
            standardized = self.standardize_image(img)
            
            # Cache management
            if len(self.image_cache) >= self.max_cache_size:
                self.image_cache.pop(next(iter(self.image_cache)))
            
            self.image_cache[image_path] = standardized
            return standardized

        except Exception as e:
            if self.debuge:
                print(f"Image loading error: {str(e)}")
            return None

    def get_sift_features(self, img_path):
        try:
            if img_path in self.sift_cache:
                return self.sift_cache[img_path]
                
            img = self.load_and_prepare_image(img_path)
            if img is None:
                return None, None
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            kp, des = self.sift.detectAndCompute(gray, None)
            
            if len(self.sift_cache) >= self.max_cache_size:
                self.sift_cache.pop(next(iter(self.sift_cache)))
            
            self.sift_cache[img_path] = (kp, des)
            return kp, des
            
        except Exception as e:
            if self.debuge:
                print(f"SIFT feature extraction error: {str(e)}")
            return None, None

    def get_hog_features(self, img_path):
        if img_path in self.hog_cache:
            return self.hog_cache[img_path]
        img = self.load_and_prepare_image(img_path)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, self.hog_size)
        hog = cv2.HOGDescriptor()
        features = hog.compute(resized)
        self.hog_cache[img_path] = features
        return features

    def get_fourier_features(self, img_path):
        if img_path in self.fourier_cache:
            return self.fourier_cache[img_path]
        img = self.load_and_prepare_image(img_path)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.log(np.abs(f_shift) + 1)
        self.fourier_cache[img_path] = magnitude_spectrum
        return magnitude_spectrum

    def process_comparison(self, args):
        target_path, compare_path, use_mirror = args
        try:
            img1 = self.load_and_prepare_image(target_path)
            img2 = self.load_and_prepare_image(compare_path)
            if img1 is None or img2 is None:
                if self.debuge: print(f"Failed to load images")
                return None

            scores = {
                'histogram': self.compare_histogram(img1, img2),
                'phash': self.compare_phash(target_path, compare_path),
                'ssim': self.compare_ssim(img1, img2),
                'mse': self.compare_mse(img1, img2),
                'hog': self.compare_hog(target_path, compare_path),
                'fourier': self.compare_fourier(target_path, compare_path),
                'sift': self.compare_sift(target_path, compare_path)
            }

            if self.debuge:
                print(f"\nComparison scores for {os.path.basename(target_path)} vs {os.path.basename(compare_path)}:")
                for method, score in scores.items():
                    print(f"{method}: {score:.3f}")

            weighted_score = sum(scores[method] * self.weights[method] 
                               for method in scores.keys())
            weighted_score /= sum(self.weights.values())

            if self.debuge:
                print(f"Final weighted score: {weighted_score:.3f}\n")

            return {
                'target': target_path,
                'compare': compare_path,
                'score': weighted_score,
                'scores': scores
            }

        except Exception as e:
            if self.debuge:
                print(f"Comparison error: {str(e)}")
            return None

    def compare_histogram(self, img1, img2):
        try:
            hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
            hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
            hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
            cv2.normalize(hist1, hist1)
            cv2.normalize(hist2, hist2)
            return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        except Exception as e:
            if self.debuge: print(f"Histogram error: {str(e)}")
            return 0.0

    def compare_phash(self, img1_path, img2_path):
        try:
            if (img1_path, img2_path) in self.phash_cache:
                return self.phash_cache[(img1_path, img2_path)]
            hash1 = imagehash.average_hash(Image.open(img1_path))
            hash2 = imagehash.average_hash(Image.open(img2_path))
            similarity = 1 - (hash1 - hash2) / len(hash1.hash)**2
            self.phash_cache[(img1_path, img2_path)] = similarity
            return similarity
        except Exception as e:
            if self.debuge: print(f"pHash error: {str(e)}")
            return 0.0

    def compare_ssim(self, img1, img2):
        try:
            # Convert to Lab color space for better perceptual comparison
            img1_lab = cv2.cvtColor(img1, cv2.COLOR_BGR2Lab)
            img2_lab = cv2.cvtColor(img2, cv2.COLOR_BGR2Lab)

            # Ensure same dimensions
            if img1_lab.shape != img2_lab.shape:
                img2_lab = cv2.resize(img2_lab, (img1_lab.shape[1], img1_lab.shape[0]))

            # Normalize each channel
            img1_norm = img1_lab.astype(np.float32) / 255.0
            img2_norm = img2_lab.astype(np.float32) / 255.0

            # Calculate SSIM with optimized parameters
            similarity = structural_similarity(
                img1_norm, img2_norm,
                multichannel=True,
                channel_axis=2,
                gaussian_weights=True,
                sigma=1.5,
                win_size=11,
                K1=0.01,
                K2=0.03,
                use_sample_covariance=False,
                data_range=1.0
            )

            # Scale similarity to emphasize differences
            similarity = np.clip((similarity + 1.0) / 1.5, 0, 1)

            return similarity

        except Exception as e:
            if self.debuge:
                print(f"SSIM error: {str(e)}")
            return 0.0

    def compare_mse(self, img1, img2):
        try:
            err = np.sum((img1.astype("float") - img2.astype("float")) ** 2)
            err /= float(img1.shape[0] * img1.shape[1])
            return 1 - (err / 255**2)
        except Exception as e:
            if self.debuge: print(f"MSE error: {str(e)}")
            return 0.0

    def compare_hog(self, img1_path, img2_path):
        try:
            if (img1_path, img2_path) in self.hog_cache:
                return self.hog_cache[(img1_path, img2_path)]
                
            # More detailed HOG parameters
            win_size = (128, 128)
            block_size = (16, 16)
            block_stride = (8, 8)
            cell_size = (8, 8)
            nbins = 12  # Increased bins
            
            img1 = self.load_and_prepare_image(img1_path)
            img2 = self.load_and_prepare_image(img2_path)
            
            if img1 is None or img2 is None:
                return 0.0
                
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            hog = cv2.HOGDescriptor(win_size, block_size, block_stride, cell_size, nbins)
            h1 = hog.compute(gray1)
            h2 = hog.compute(gray2)
            
            # Improved similarity calculation
            similarity = 1 - (np.linalg.norm(h1 - h2) / (np.linalg.norm(h1) + np.linalg.norm(h2)))
            similarity = min(1.0, similarity * 2.0)  # Scale up similarity
            
            self.hog_cache[(img1_path, img2_path)] = similarity
            return similarity
            
        except Exception as e:
            if self.debuge:
                print(f"HOG error: {str(e)}")
            return 0.0

    def compare_fourier(self, img1_path, img2_path):
        try:
            if (img1_path, img2_path) in self.fourier_cache:
                return self.fourier_cache[(img1_path, img2_path)]
            
            img1 = self.load_and_prepare_image(img1_path)
            img2 = self.load_and_prepare_image(img2_path)
            
            if img1 is None or img2 is None:
                return 0.0
            
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            f1 = np.fft.fft2(gray1)
            f2 = np.fft.fft2(gray2)
            
            # Improved spectrum comparison
            magnitude1 = np.abs(np.fft.fftshift(f1))
            magnitude2 = np.abs(np.fft.fftshift(f2))
            
            similarity = 1 - np.sum(np.abs(magnitude1 - magnitude2)) / np.sum(magnitude1 + magnitude2)
            similarity = (similarity + 1) / 2  # Normalize to [0,1]
            
            self.fourier_cache[(img1_path, img2_path)] = similarity
            return max(0.0, similarity)
        except Exception as e:
            if self.debuge: print(f"Fourier error: {str(e)}")
            return 0.0

    def compare_sift(self, img1_path, img2_path):
        try:
            kp1, des1 = self.get_sift_features(img1_path)
            kp2, des2 = self.get_sift_features(img2_path)

            if des1 is None or des2 is None or len(des1) < 2 or len(des2) < 2:
                return 0.0

            # Improved matching
            matches = self.matcher.knnMatch(des1, des2, k=2)
            good_matches = []
            potential_matches = []

            # Two-stage matching
            for m, n in matches:
                if m.distance < 0.75 * n.distance:  # First stage
                    potential_matches.append(m)

            if len(potential_matches) > 4:
                # Extract matched keypoints
                src_pts = np.float32([kp1[m.queryIdx].pt for m in potential_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in potential_matches]).reshape(-1, 1, 2)

                # Find homography and mask
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                matches_mask = mask.ravel().tolist()

                # Filter matches using homography
                good_matches = [m for i, m in enumerate(potential_matches) if matches_mask[i]]

                # Calculate weighted similarity
                if len(good_matches) > 0:
                    # Distance-based weighting
                    distances = np.array([m.distance for m in good_matches])
                    min_dist = distances.min()
                    max_dist = distances.max()
                    
                    # Normalize distances and calculate weights
                    if max_dist - min_dist > 0:
                        weights = 1 - ((distances - min_dist) / (max_dist - min_dist))
                    else:
                        weights = np.ones_like(distances)

                    # Calculate weighted similarity score
                    match_ratio = len(good_matches) / min(len(des1), len(des2))
                    quality_score = np.mean(weights)
                    geometric_score = len(good_matches) / len(potential_matches)

                    # Combine scores
                    similarity = (match_ratio * 0.4 + quality_score * 0.4 + geometric_score * 0.2)
                    similarity = min(1.0, similarity * 2.5)  # Scale up but cap at 1.0

                    if self.debuge:
                        print(f"SIFT stats: Matches={len(good_matches)}, Quality={quality_score:.3f}, Geometric={geometric_score:.3f}")

                    return similarity

            return 0.0

        except Exception as e:
            if self.debuge:
                print(f"SIFT comparison error: {str(e)}")
            return 0.0

    @lru_cache(maxsize=1000)
    def quick_compare(self, img1_path, img2_path):
        """Fast initial comparison to filter obvious non-matches"""
        try:
            img1 = cv2.resize(cv2.imread(img1_path), self.quick_size)
            img2 = cv2.resize(cv2.imread(img2_path), self.quick_size)
            if img1 is None or img2 is None:
                return 0.0
            return self.compare_histogram(img1, img2)
        except:
            return 0.0

    def process_batch(self, batch):
        results = []
        for target_path, compare_path, use_mirror in batch:
            # Quick initial check
            if self.quick_compare(target_path, compare_path) < 0.5:
                continue
            
            # Full comparison only if quick check passes
            result = self.process_comparison((target_path, compare_path, use_mirror))
            if result:
                results.append(result)
                
        return results

    def process_comparisons(self, target_folder, compare_folder, use_mirror):
        pr = cProfile.Profile()
        pr.enable()
        
        try:
            if self.debuge:
                print(f"Target folder: {target_folder}")
                print(f"Compare folder: {compare_folder}")
                print(f"Contents of target folder: {os.listdir(target_folder)}")
                print(f"Contents of compare folder: {os.listdir(compare_folder)}")

            # Verify directories exist
            if not os.path.exists(target_folder) or not os.path.exists(compare_folder):
                print("One or both directories do not exist")
                return []

            # Get image files with debug info
            target_images = [os.path.join(target_folder, f) for f in os.listdir(target_folder) 
                            if f.lower().endswith(self.supported_formats)]
            compare_images = [os.path.join(compare_folder, f) for f in os.listdir(compare_folder)
                            if f.lower().endswith(self.supported_formats)]

            if self.debuge:
                print(f"Found {len(target_images)} target images")
                print(f"Found {len(compare_images)} compare images")
                print(f"Target images: {target_images}")
                print(f"Compare images: {compare_images}")

            comparison_params = [
                (t, c, use_mirror) for t in target_images for c in compare_images
            ]

            batch_size = min(1000, len(comparison_params))
            results = []
            
            for i in range(0, len(comparison_params), batch_size):
                batch = comparison_params[i:i + batch_size]
                batch_results = self.process_batch(batch)
                results.extend(batch_results)

            return results

        finally:
            pr.disable()
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats()
            print(s.getvalue())

    def compare_all(self, target_dir, compare_dir, use_mirror=False):
        try:
            self.start_time = time.time()
            self.completed_comparisons = 0
            
            # Calculate total comparisons
            target_images = [f for f in os.listdir(target_dir) 
                           if f.lower().endswith(self.supported_formats)]
            compare_images = [f for f in os.listdir(compare_dir) 
                            if f.lower().endswith(self.supported_formats)]
            
            self.total_comparisons = len(target_images) * len(compare_images)
            
            comparisons = []
            for target in target_images:
                target_path = os.path.join(target_dir, target)
                for comp in compare_images:
                    comp_path = os.path.join(compare_dir, comp)
                    comparisons.append((target_path, comp_path, use_mirror))

            matches = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for i in range(0, len(comparisons), self.batch_size):
                    batch = comparisons[i:i + self.batch_size]
                    futures.append(executor.submit(self.process_batch, batch))
                    
                    # Monitor memory usage
                    if psutil.Process().memory_percent() > self.memory_threshold:
                        self.clear_caches()
                
                results = []
                for future in as_completed(futures):
                    results.extend(future.result())
            
            return self.process_results(results)

        except Exception as e:
            if self.debuge:
                print(f"Global comparison error: {str(e)}")
            return {"status": "0", "message": str(e)}

    def create_match_directory(self, result):
        base_dir = os.path.join("materiel", "ahce_match")
        os.makedirs(base_dir, exist_ok=True)
        match_dir = os.path.join(base_dir, f"MATCH_{len(os.listdir(base_dir)) + 1}")
        os.makedirs(match_dir)
        
        for img_path in [result['target'], result['compare']]:
            shutil.copy2(img_path, match_dir)
        
        return match_dir
    
    def get_progress(self):
        current_time = time.time()
        
        if not self.start_time:
            return {"status": "idle"}
            
        if self.last_update and (current_time - self.last_update) < self.update_interval:
            return {"status": "waiting"}
            
        self.last_update = current_time
        elapsed_time = current_time - self.start_time
        
        if self.completed_comparisons > 0:
            self.avg_time_per_comparison = elapsed_time / self.completed_comparisons
            remaining = self.total_comparisons - self.completed_comparisons
            eta = remaining * self.avg_time_per_comparison
            
            return {
                "status": "running",
                "progress": self.completed_comparisons / self.total_comparisons,
                "remaining_time": eta,
                "completed": self.completed_comparisons,
                "total": self.total_comparisons,
                "elapsed": elapsed_time
            }
        return {"status": "starting"}

# Create global instance
comparator = ImageComparator()

@eel.expose
def get_progress():
    return comparator.get_progress()

@eel.expose
def browse_folder():
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring dialog to front
        folder = filedialog.askdirectory(
            title="Select Folder",
            mustexist=True
        )
        root.destroy()
        return folder if folder else ""
    except Exception as e:
        print(f"Error in folder selection: {str(e)}")
        return ""

@eel.expose
def start_comparison(target_dir, compare_dir, use_mirror):
    global comparator
    return comparator.compare_all(target_dir, compare_dir, use_mirror)

@eel.expose
def exit_program():
    os._exit(0)

if __name__ == "__main__":
    eel.start('ahce.html', size=(1920, 1080))