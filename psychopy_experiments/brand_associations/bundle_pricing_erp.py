# -*- coding: utf-8 -*-
"""
Bundle Pricing Zero Price Effect (N400/ERP) — PsychoPy
Focal + Tie-in product bundles with three price frames: NP, LP, ZP.
Response: BUY vs NOT BUY (counterbalanced across participants).
Per-trial CSV with timing, keys, RTs, and purchase tracking.

Paradigm based on:
- 45 complementary bundles (90 products total)
- 3 price conditions: NP (20% discount), LP (low token ₾0.1), ZP (zero price tie-in)
- 135 trials total (45 × 3), split into 3 blocks
- Virtual allocation of ₾70 per trial (resets each trial)
- Penalty system for insufficient purchases
- One random bundle selected for potential real shipping
"""

USE_LSL = False  # Set to True to enable LSL markers for EEG

if USE_LSL:
    from pylsl import StreamInfo, StreamOutlet
from psychopy import visual, core, event, logging, gui
from psychopy.hardware import keyboard
from PIL import Image
import random
import os
import csv
import math
from datetime import datetime

# =============================================================================
# TIMING PARAMETERS (in seconds)
# =============================================================================
FIXATION_TIME = 0.000          # 1000 ms fixation cross
BUNDLE_PREVIEW_TIME = 0.000    # 2000 ms bundle presentation (no price)
EMPTY_SCREEN_INTERVAL = (0.400, 0.600)  # 400–600 ms empty screen (randomized)
PRICE_RESPONSE_TIME = 1.000    # 4000 ms bundle with price (response window)
# Note: Only responses within 4s are valid for behavioral analyses

# =============================================================================
# TRIAL & BLOCK STRUCTURE
# =============================================================================
N_BUNDLES = 40                 # 45 complementary bundles
PRICE_CONDITIONS = ['NP']  # Normal, Low, Zero price conditions
N_TRIALS_TOTAL = N_BUNDLES * len(PRICE_CONDITIONS)  # 135 trials
TRIALS_PER_BLOCK = 40          # 3 blocks of 45 trials each
N_BLOCKS = 3

# =============================================================================
# VIRTUAL MONEY & PENALTY SYSTEM
# =============================================================================
ALLOCATION_PER_TRIAL = 70.0    # ₾70 virtual allocation PER TRIAL (resets each trial)
LOW_TOKEN_PRICE = 0.1          # ₾0.1 for LP tie-in product
DISCOUNT_PERCENT = 20          # 20% discount for NP condition

# Penalty thresholds
PENALTY_THRESHOLDS = [
    (20, 20.0),   # <20 bundles bought → lose ₾20
    (25, 10.0),   # 20-24 bundles → lose ₾10
    (30, 5.0),    # 25-29 bundles → lose ₾5
    (float('inf'), 0.0)  # ≥30 bundles → no penalty
]

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================
FULLSCR = True
WIN_SIZE = [1280, 800]
BG_COLOR = [0.7, 0.7, 0.7]     # Gray background
FONT_NAME = 'DejaVu Sans'
TITLE = "Bundle Pricing Study"
PRICE_COLOR = 'red'            # All prices in red

# Product display positions
# Fixed distances from center (fixation cross) to image edges
FOCAL_RIGHT_EDGE_X = -50       # Right edge of left (focal) image distance from center
TIEIN_LEFT_EDGE_X = 50         # Left edge of right (tiein) image distance from center
IMAGE_CENTER_Y = 60             # Vertical center for images
PRICE_OFFSET_BELOW_IMAGE = 30   # Pixels below image bottom for price display
PRICE_TEXT_HEIGHT = 36          # Price text size (larger than before)

# Image settings
IMAGE_MAX_SIZE = (600, 480)    # Max bounding box for product images (w, h)

# =============================================================================
# RESPONSE KEYS (counterbalanced)
# =============================================================================
# Group A: "1" = BUY, "3" = NOT BUY
# Group B: "1" = NOT BUY, "3" = BUY
KEY_1 = 'num_1'  # or '1' depending on keyboard
KEY_3 = 'num_3'  # or '3' depending on keyboard
# Fallback to regular number keys
KEY_1_ALT = '1'
KEY_3_ALT = '3'

# =============================================================================
# LSL MARKERS
# =============================================================================
MARKER_FIXATION = 10
MARKER_BUNDLE_PREVIEW = 20
MARKER_BUNDLE_PRICE_NP = 31
MARKER_BUNDLE_PRICE_LP = 32
MARKER_BUNDLE_PRICE_ZP = 33
MARKER_RESPONSE_BUY = 41
MARKER_RESPONSE_NOBUY = 42
MARKER_NO_RESPONSE = 50

# =============================================================================
# FILE PATHS
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
OUT_CSV = os.path.join(BASE_DIR, f"bundle_pricing_{TIMESTAMP}.csv")

# =============================================================================
# IMAGE FOLDER STRUCTURE
# =============================================================================
# Images should be organized as:
#   media/bundles/
#       bundle_01/
#           focal.jpg (or .png)
#           tiein.jpg (or .png)
#       bundle_02/
#           focal.jpg
#           tiein.jpg
#       ...
#       bundle_45/
#           focal.jpg
#           tiein.jpg
#
# Alternatively, flat structure:
#   media/bundles/
#       bundle_01_focal.jpg
#       bundle_01_tiein.jpg
#       ...
MEDIA_DIR = os.path.join(BASE_DIR, "media")
BUNDLES_DIR = os.path.join(MEDIA_DIR, "bundles")

# =============================================================================
# BUNDLE DEFINITIONS
# =============================================================================
# Each bundle: (bundle_id, focal_product_name, tiein_product_name, 
#               base_focal_price, base_tiein_price)
# Names are saved to CSV but NOT displayed (only images are shown)
# Prices should be mean of two online shops as per study design

BUNDLES = [
    # Format: (id, focal_name, tiein_name, focal_base_price, tiein_base_price)
    (1, "Wireless Mouse (Dell WM126 Black)", "Gembird mouse Pad Black", 51.12, 3.0),
    (2, "2E Membrane keyboard KG350 Gaming", "Keyboard Cover", 55.0, 15.0),
    (3, "Hoco J87 Tacker PD20W+QC3.0 Power Bank (10000mAh) Black", "Hoco X86 Micro Spear silicone charging data cable Black", 49.0, 9.0),
    (4, "Proove Wireless Earphones Mainstream TWS white", "BLACK CASE FOR AIRPODS 3", 58.0, 12.0),
    (5, "Webcam (HD camera mini packing)", "RK-12 LED Light", 43.0, 16.0),
    (6, "Vention TGKBD Type-C to 4-Port", "Ugreen USB-C to USB-C PD Fast Charging Cable", 49.0, 19.0),
    (7, "Electric Kettle (ADLER AD1224)", "Tea Cup with Filter", 45.0, 7.59),
    (8, "Electric Stove (ARNICA ID 77610)", "Pan (HASCEVHER PICCOLO ID 100424)", 38.0, 14.2),
    (9, "Rice (N1 Long Grain 900g)", "Spices (Black Pepper)", 4.29, 1.25),
    (10, "Olive Oil (Extra Virgin 0.5L)", "Salad Bowl", 25.0, 4.0),
    (11, "Bacon", "Eggs", 11.25, 4.75),
    (12, "Pesto", "Pasta Barilla (Fussili)", 23.4, 5.95),
    (13, "Cavear", "Butter (President)", 49.95, 9.95),
    (14, "Sausage (780g)", "Mustard", 14.5, 1.75),
    (15, "Nuts (Peanuts 120g)", "Dried Fruits", 11.95, 4.5),
    (16, "Chocolate Set (90g)", "Coffee", 16.95, 4.8),
    (17, "Jackobs", "Coffee mug", 35.0, 17.68),
    (18, "Red Wine 'Gonadze' Khvanchkara (Semi-Sweet) 0.75L", "Wine Bottle Opener OEM TM39002", 39.95, 14.0),
    (19, "Whiskey (0.75L)", "Leonardo Swing Whisky Glass", 59.9, 9.5),
    (20, "Arak (Georgian Brandy)", "Energy Drink Red Bull (250ml)", 50.0, 5.95),
    (21, "Tea Box", "Greenfield Tea", 39.9, 4.95),
    (22, "Beer", "Peanuts", 14.0, 3.2),
    (23, "Toilet Paper (Selpak 32pcs)", "Wet Wipes", 32.5, 6.8),
    (24, "Fito - Nourishment Shampoo for Dry Hair Sulfate-Free 250ml", "Fito - Nourishment Conditioner for Dry Hair 175ml", 30.95, 24.95),
    (25, "Liquid Soap Dispenser", "Liquid Soap", 49.2, 6.5),
    (26, "Razor", "Shaving Foam", 59.9, 9.95),
    (27, "Nail Care Set", "Tweezers", 62.89, 5.95),
    (28, "Coconut Body Lotion", "Soap", 45.0, 19.0),
    (29, "Electric Toothbrush Bicofident", "Toothpaste (LACALUT 75ml)", 43.5, 10.56),
    (30, "Floor Cleaning Mop", "Mop Replacement Head", 62.0, 7.4),
    (31, "Designworks Ink - Notebook Twin Wire", "Pen", 49.99, 3),
    (32, "Sapiens", "Bookmark", 24.9, 3.0),
    (33, "Board", "Markers", 49.0, 4.75),
    (34, "Cutting Board", "Knife", 44.9, 19.0),
    (35, "Candlestick", "Candle", 39.9, 8.0),
    (36, "Lunch container", "Lunch Bag", 44.0, 15.0),
    (37, "FAIRY Dishwashing Liquid Lemon 1.5L", "Dishwashing Sponge VILEDA", 11.55, 2.25),
    (38, "Table Lamp", "Light Bulb", 57.0, 12.0),
    (39, "Hascevher 28cm Granite Pan without Lid", "Drevotvar 29.5cm Wooden Spoon", 34.0, 5.3),
    (40, "Flashlight", "Battery", 67.0, 5),
]

# Ensure we have exactly N_BUNDLES
assert len(BUNDLES) == N_BUNDLES, f"Expected {N_BUNDLES} bundles, got {len(BUNDLES)}"

# =============================================================================
# LSL SETUP
# =============================================================================
if USE_LSL:
    info = StreamInfo(
        name='PsychopyMarkerStream',
        type='Markers',
        channel_count=1,
        channel_format='int32',
        source_id='bundle_pricing_erp'
    )
    outlet = StreamOutlet(info)

logging.console.setLevel(logging.INFO)


def send_marker(win, value):
    """Send a marker value exactly on next flip."""
    if USE_LSL:
        win.callOnFlip(outlet.push_sample, [int(value)])


def get_participant_info():
    """Dialog to get participant ID and counterbalance group."""
    dlg = gui.Dlg(title=TITLE)
    dlg.addField('Participant ID:', '')
    dlg.addField('Age:', '')
    dlg.addField('Response Mapping (A or B):', 'A')
    data = dlg.show()
    
    if dlg.OK:
        pid = data[0] if data[0] else f"P{random.randint(1000, 9999)}"
        age = data[1] if data[1] else "N/A"
        group = data[2].upper() if data[2].upper() in ['A', 'B'] else 'A'
        return pid, age, group
    else:
        core.quit()


def fitted_size_for_image(img_path, max_size):
    """
    Compute (w,h) that fits 'img_path' inside 'max_size' while preserving aspect ratio.
    max_size is (max_w, max_h) in pixels.
    """
    try:
        with Image.open(img_path) as im:
            w, h = im.size
        max_w, max_h = max_size
        scale = min(max_w / float(w), max_h / float(h))
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        return new_w, new_h
    except Exception as e:
        logging.warning(f"Could not read image {img_path}: {e}")
        return max_size  # Fallback to max size


def get_bundle_image_paths(bundle_id):
    """
    Get image paths for focal and tie-in products of a bundle.
    Tries multiple folder structures and file extensions.
    Returns: (focal_path, tiein_path) or (None, None) if not found
    """
    extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
    
    # Try folder structure: bundles/bundle_XX/focal.ext, bundles/bundle_XX/tiein.ext
    bundle_folder = os.path.join(BUNDLES_DIR, f"bundle_{bundle_id:02d}")
    if os.path.isdir(bundle_folder):
        focal_path = None
        tiein_path = None
        for ext in extensions:
            if focal_path is None and os.path.exists(os.path.join(bundle_folder, f"focal{ext}")):
                focal_path = os.path.join(bundle_folder, f"focal{ext}")
            if tiein_path is None and os.path.exists(os.path.join(bundle_folder, f"tiein{ext}")):
                tiein_path = os.path.join(bundle_folder, f"tiein{ext}")
        if focal_path and tiein_path:
            return focal_path, tiein_path
    
    # Try flat structure: bundles/bundle_XX_focal.ext, bundles/bundle_XX_tiein.ext
    for ext in extensions:
        focal_path = os.path.join(BUNDLES_DIR, f"bundle_{bundle_id:02d}_focal{ext}")
        tiein_path = os.path.join(BUNDLES_DIR, f"bundle_{bundle_id:02d}_tiein{ext}")
        if os.path.exists(focal_path) and os.path.exists(tiein_path):
            return focal_path, tiein_path
    
    return None, None


def create_placeholder_image(width, height, text, bg_color=(200, 200, 200), text_color=(50, 50, 50)):
    """
    Create a placeholder image with text (for when actual product images aren't available).
    Returns the path to the created temporary image.
    """
    from PIL import ImageDraw, ImageFont
    
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Use default font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()
    
    # Center text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Draw border
    draw.rectangle([0, 0, width-1, height-1], outline=(100, 100, 100), width=2)
    
    # Save to temp file
    temp_dir = os.path.join(BASE_DIR, "temp_images")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"placeholder_{text.replace(' ', '_')[:20]}_{random.randint(1000,9999)}.png")
    img.save(temp_path)
    return temp_path


def calculate_prices(bundle, condition):
    """
    Calculate prices for focal and tie-in products based on condition.
    
    NP (Normal Price): 20% discount on total bundle
    ZP (Zero Price): Tie-in free, focal adjusted so total = NP total
    LP (Low Price): Tie-in at ₾0.1, focal same as ZP focal
    
    Returns: (focal_price, tiein_price, total_price)
    """
    _, _, _, base_focal, base_tiein = bundle
    base_total = base_focal + base_tiein
    
    if condition == 'NP':
        # 20% discount on bundle
        discount = base_total * (DISCOUNT_PERCENT / 100.0)
        total = base_total - discount
        # Distribute discount proportionally
        focal_price = base_focal * (1 - DISCOUNT_PERCENT / 100.0)
        tiein_price = base_tiein * (1 - DISCOUNT_PERCENT / 100.0)
    
    elif condition == 'ZP':
        # Tie-in is free, total same as NP
        np_total = base_total * (1 - DISCOUNT_PERCENT / 100.0)
        tiein_price = 0.0
        focal_price = np_total  # Focal absorbs the cost
        total = np_total
    
    elif condition == 'LP':
        # Tie-in at ₾0.1, focal same as ZP focal
        np_total = base_total * (1 - DISCOUNT_PERCENT / 100.0)
        tiein_price = LOW_TOKEN_PRICE
        focal_price = np_total  # Same as ZP focal
        total = focal_price + tiein_price
    
    else:
        raise ValueError(f"Unknown condition: {condition}")
    
    return round(focal_price, 2), round(tiein_price, 2), round(total, 2)


def build_trials():
    """
    Build trial list with pseudorandom constraints:
    - 135 trials (45 bundles × 3 conditions)
    - Split into 3 blocks of 45 trials
    - Same bundle cannot appear within 3 consecutive trials
    
    Uses efficient iterative repair algorithm with guaranteed O(n) complexity.
    
    Why this is efficient:
    - With 45 bundles and only 3 occurrences each, the constraint is sparse
    - The probability of random shuffle satisfying constraint is high (~90%+)
    - Iterative repair fixes violations locally in O(1) per violation
    - Worst case: O(n) repairs, each O(n) to find swap target = O(n²)
    - Average case: Very few repairs needed after initial shuffle
    """
    # Create all trial combinations
    all_trials = []
    for bundle in BUNDLES:
        for condition in PRICE_CONDITIONS:
            focal_price, tiein_price, total_price = calculate_prices(bundle, condition)
            
            # Get image paths
            focal_img, tiein_img = get_bundle_image_paths(bundle[0])
            
            all_trials.append({
                'bundle_id': bundle[0],
                'focal_name': bundle[1],
                'tiein_name': bundle[2],
                'focal_img_path': focal_img,
                'tiein_img_path': tiein_img,
                'condition': condition,
                'focal_price': focal_price,
                'tiein_price': tiein_price,
                'total_price': total_price,
            })
    
    def has_violation_at(trials, i):
        """Check if position i violates the 3-consecutive constraint."""
        if i < 0 or i >= len(trials):
            return False
        bundle_id = trials[i]['bundle_id']
        # Check if same bundle appears at i-1, i, or i+1, i+2
        for offset in [-2, -1, 1, 2]:
            j = i + offset
            if 0 <= j < len(trials) and j != i:
                if trials[j]['bundle_id'] == bundle_id:
                    # Check if they're within 3 consecutive
                    if abs(offset) <= 2:
                        return True
        return False
    
    def find_valid_swap(trials, i):
        """Find a valid position to swap with position i to fix violation."""
        bundle_id = trials[i]['bundle_id']
        # Try random positions first for better distribution
        indices = list(range(len(trials)))
        random.shuffle(indices)
        
        for j in indices:
            if abs(i - j) <= 2:  # Skip nearby positions
                continue
            
            # Check if swapping would create new violations
            trial_j_id = trials[j]['bundle_id']
            
            # Temporarily swap and check
            trials[i], trials[j] = trials[j], trials[i]
            
            # Check if swap fixes without creating new violations
            ok = True
            for pos in [i-2, i-1, i, i+1, i+2, j-2, j-1, j, j+1, j+2]:
                if 0 <= pos < len(trials):
                    if has_violation_at(trials, pos):
                        ok = False
                        break
            
            # Swap back
            trials[i], trials[j] = trials[j], trials[i]
            
            if ok:
                return j
        
        return None
    
    def shuffle_with_constraint(trials, max_repair_passes=50):
        """Shuffle trials and repair violations iteratively."""
        shuffled = trials.copy()
        random.shuffle(shuffled)
        
        for pass_num in range(max_repair_passes):
            violations_fixed = 0
            
            for i in range(len(shuffled)):
                if has_violation_at(shuffled, i):
                    j = find_valid_swap(shuffled, i)
                    if j is not None:
                        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
                        violations_fixed += 1
            
            # Check if all violations are fixed
            all_ok = True
            for i in range(len(shuffled)):
                if has_violation_at(shuffled, i):
                    all_ok = False
                    break
            
            if all_ok:
                logging.info(f"Shuffling completed after {pass_num + 1} repair passes")
                return shuffled
        
        logging.warning(f"Could not fully satisfy constraint after {max_repair_passes} passes")
        return shuffled
    
    # Shuffle trials with constraint
    shuffled_trials = shuffle_with_constraint(all_trials)
    
    logging.info(f"Built {len(shuffled_trials)} trials in {N_BLOCKS} blocks")
    return shuffled_trials


def create_csv_header(selected_bundle_id):
    """Create output CSV with header and metadata."""
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        # Metadata row
        w.writerow(["# SELECTED_BUNDLE_FOR_SHIPPING", selected_bundle_id])
        w.writerow([])
        # Header
        w.writerow([
            "timestamp_iso",
            "participant_id",
            "age",
            "response_group",
            "trial_index",
            "block",
            "bundle_id",
            "focal_product",
            "tiein_product",
            "condition",
            "focal_price",
            "tiein_price",
            "total_price",
            "allocation_per_trial",
            "response_key",
            "response",  # BUY or NOBUY
            "rt_ms",
            "valid_response",  # 1 if response within 4s, 0 otherwise
            "is_selected_bundle",  # 1 if this is the randomly selected bundle
            "bundles_bought_cumulative",
        ])


def calculate_penalty(bundles_bought):
    """Calculate penalty based on number of bundles bought."""
    for threshold, penalty in PENALTY_THRESHOLDS:
        if bundles_bought < threshold:
            return penalty
    return 0.0


def format_price(price):
    """
    Format price for display using Georgian Lari symbol (₾).
    - Integers shown without decimals (e.g., 25 ₾)
    - Decimals shown without trailing zeros (e.g., 0.1 ₾)
    - Zero shown as 0 ₾
    """
    if price == 0:
        return "0 ₾"
    elif price == int(price):
        return f"{int(price)} ₾"
    else:
        # Remove trailing zeros from decimal
        formatted = f"{price:.2f}".rstrip('0').rstrip('.')
        return f"{formatted} ₾"


def main():
    # Get participant info
    participant_id, age, response_group = get_participant_info()
    
    # Randomly select one bundle that will be shipped if bought
    selected_bundle_id = random.choice([b[0] for b in BUNDLES])
    selected_bundle_name = next(b[1] for b in BUNDLES if b[0] == selected_bundle_id)
    selected_bundle_bought = False
    logging.info(f"Selected bundle for potential shipping: {selected_bundle_id} ({selected_bundle_name})")
    
    # Determine key mappings based on group
    if response_group == 'A':
        # Group A: 1 = BUY, 3 = NOT BUY
        buy_keys = [KEY_1, KEY_1_ALT]
        nobuy_keys = [KEY_3, KEY_3_ALT]
        key_instruction = '"1" = BUY, "3" = NOT BUY'
    else:
        # Group B: 1 = NOT BUY, 3 = BUY
        buy_keys = [KEY_3, KEY_3_ALT]
        nobuy_keys = [KEY_1, KEY_1_ALT]
        key_instruction = '"1" = NOT BUY, "3" = BUY'
    
    all_resp_keys = buy_keys + nobuy_keys
    
    # Initialize window
    win = visual.Window(size=WIN_SIZE, units='pix', color=BG_COLOR, fullscr=FULLSCR)
    kb = keyboard.Keyboard()
    logging.info(f"Window initialized: {win.size} px, fullscr={FULLSCR}")
    logging.info(f"Participant: {participant_id}, Group: {response_group}")
    
    # Create visual stimuli
    fixation = visual.TextStim(win, text='+', height=60, color='black', font=FONT_NAME)
    
    # Image stimuli for products (will be updated per trial)
    # Positions will be calculated dynamically based on image sizes
    focal_img_stim = visual.ImageStim(win, image=None, pos=(0, IMAGE_CENTER_Y), size=None, anchor='right')
    tiein_img_stim = visual.ImageStim(win, image=None, pos=(0, IMAGE_CENTER_Y), size=None, anchor='left')
    
    # Price text stimuli - all in red (positions will be calculated dynamically)
    focal_price_text = visual.TextStim(win, text='', height=PRICE_TEXT_HEIGHT, color=PRICE_COLOR,
                                        pos=(0, 0), font=FONT_NAME, bold=True)
    tiein_price_text = visual.TextStim(win, text='', height=PRICE_TEXT_HEIGHT, color=PRICE_COLOR,
                                        pos=(0, 0), font=FONT_NAME, bold=True)
    # Total price display removed per design requirement
    
    # Instructions screen
    instructions = visual.TextStim(
        win,
        text=(
            f"{TITLE}\n\n"
            f"You will see product bundles (focal product on LEFT, tie-in product on RIGHT).\n\n"
            f"After viewing the bundle, prices will appear.\n"
            f"Decide whether to BUY or NOT BUY the bundle.\n\n"
            f"Your response keys: {key_instruction}\n\n"
            f"You have {int(ALLOCATION_PER_TRIAL)} ₾ per trial.\n\n"
            f"IMPORTANT:\n"
            f"• Buying fewer than 20 bundles → lose 20 ₾\n"
            f"• Buying 20-24 bundles → lose 10 ₾\n"
            f"• Buying 25-29 bundles → lose 5 ₾\n"
            f"• Buying 30+ bundles → no penalty\n\n"
            f"One bundle has been randomly selected.\n"
            f"If you buy it, you will actually receive it!\n\n"
            f"Respond within 4 seconds of seeing prices.\n\n"
            f"Press SPACE to begin."
        ),
        height=20, color='black', wrapWidth=1000, font=FONT_NAME, alignText='center'
    )
    
    # Rest screen between blocks
    rest_text = visual.TextStim(win, text='', height=26, color='black',
                                 wrapWidth=900, font=FONT_NAME, alignText='center')
    
    # End screen
    end_text = visual.TextStim(win, text='', height=26, color='black',
                                wrapWidth=900, font=FONT_NAME, alignText='center')
    
    # Build trials
    trials = build_trials()
    total_trials = len(trials)
    
    # Preload/create placeholder images for bundles without actual images
    placeholder_cache = {}
    for trial in trials:
        if trial['focal_img_path'] is None:
            cache_key = f"focal_{trial['bundle_id']}"
            if cache_key not in placeholder_cache:
                placeholder_cache[cache_key] = create_placeholder_image(
                    IMAGE_MAX_SIZE[0], IMAGE_MAX_SIZE[1], 
                    f"[{trial['focal_name'][:15]}]"
                )
            trial['focal_img_path'] = placeholder_cache[cache_key]
        
        if trial['tiein_img_path'] is None:
            cache_key = f"tiein_{trial['bundle_id']}"
            if cache_key not in placeholder_cache:
                placeholder_cache[cache_key] = create_placeholder_image(
                    IMAGE_MAX_SIZE[0], IMAGE_MAX_SIZE[1], 
                    f"[{trial['tiein_name'][:15]}]"
                )
            trial['tiein_img_path'] = placeholder_cache[cache_key]
    
    # Show instructions
    instructions.draw()
    win.flip()
    kb.clearEvents()
    event.clearEvents()
    kb.waitKeys(keyList=['space', 'escape'])
    if any(k.name == 'escape' for k in kb.getKeys(waitRelease=False)):
        win.close()
        core.quit()
    
    # Create CSV with selected bundle info
    create_csv_header(selected_bundle_id)
    
    # Initialize tracking variables
    bundles_bought = 0
    
    # Trial loop
    for t_idx, trial in enumerate(trials):
        current_block = (t_idx // TRIALS_PER_BLOCK) + 1
        is_selected = 1 if trial['bundle_id'] == selected_bundle_id else 0
        
        # Clear events before trial
        kb.clearEvents()
        event.clearEvents()
        
        # =====================================================================
        # PHASE 1: Fixation (1000 ms)
        # =====================================================================
        send_marker(win, MARKER_FIXATION)
        fix_onset = core.getTime()
        while (core.getTime() - fix_onset) < FIXATION_TIME:
            fixation.draw()
            win.flip()
            if kb.getKeys(keyList=['escape'], waitRelease=False):
                win.close()
                core.quit()
        
        # =====================================================================
        # PHASE 2: Bundle Preview - images only, no prices (2000 ms)
        # =====================================================================
        # Load images for this trial
        focal_img_stim.image = trial['focal_img_path']
        focal_size = fitted_size_for_image(trial['focal_img_path'], IMAGE_MAX_SIZE)
        focal_img_stim.size = focal_size
        
        tiein_img_stim.image = trial['tiein_img_path']
        tiein_size = fitted_size_for_image(trial['tiein_img_path'], IMAGE_MAX_SIZE)
        tiein_img_stim.size = tiein_size
        
        # Calculate positions: focal image right edge at FOCAL_RIGHT_EDGE_X, tiein image left edge at TIEIN_LEFT_EDGE_X
        # For anchor='right', pos.x is the right edge position
        # For anchor='left', pos.x is the left edge position
        focal_img_stim.pos = (FOCAL_RIGHT_EDGE_X, IMAGE_CENTER_Y)
        tiein_img_stim.pos = (TIEIN_LEFT_EDGE_X, IMAGE_CENTER_Y)
        
        # Calculate price positions: below the lowest image bottom
        # Image bottom = center_y - height/2 (in pixels, but PsychoPy uses normalized units)
        # We need to convert pixel sizes to normalized units
        # Assuming win.size gives window size in pixels
        win_w, win_h = win.size
        focal_h_pixels = focal_size[1]
        tiein_h_pixels = tiein_size[1]
        
        # Convert pixel heights to normalized units (PsychoPy uses height units by default)
        # For 'pix' units, we can use pixel values directly
        focal_bottom_y = IMAGE_CENTER_Y - (focal_h_pixels / 2.0)
        tiein_bottom_y = IMAGE_CENTER_Y - (tiein_h_pixels / 2.0)
        lowest_bottom_y = min(focal_bottom_y, tiein_bottom_y)
        
        # Price Y position: lowest image bottom - offset
        price_y = lowest_bottom_y - PRICE_OFFSET_BELOW_IMAGE
        
        # Price X positions: aligned with image centers
        focal_center_x = FOCAL_RIGHT_EDGE_X - (focal_size[0] / 2.0)
        tiein_center_x = TIEIN_LEFT_EDGE_X + (tiein_size[0] / 2.0)
        
        focal_price_text.pos = (focal_center_x, price_y)
        tiein_price_text.pos = (tiein_center_x, price_y)
        
        send_marker(win, MARKER_BUNDLE_PREVIEW)
        preview_onset = core.getTime()
        while (core.getTime() - preview_onset) < BUNDLE_PREVIEW_TIME:
            focal_img_stim.draw()
            tiein_img_stim.draw()
            fixation.draw()
            win.flip()
            if kb.getKeys(keyList=['escape'], waitRelease=False):
                win.close()
                core.quit()
        
        # =====================================================================
        # PHASE 3: Empty Screen (400-600 ms randomized)
        # =====================================================================
        empty_duration = random.uniform(*EMPTY_SCREEN_INTERVAL)
        empty_onset = core.getTime()
        while (core.getTime() - empty_onset) < empty_duration:
            win.flip()
            if kb.getKeys(keyList=['escape'], waitRelease=False):
                win.close()
                core.quit()
        
        # =====================================================================
        # PHASE 4: Bundle with Prices - Response Window (4000 ms)
        # =====================================================================
        # Set price texts - all in red
        # (Positions already calculated in PHASE 2 based on image sizes)
        focal_price_text.text = format_price(trial['focal_price'])
        tiein_price_text.text = format_price(trial['tiein_price'])
        # Total price not displayed (only individual product prices shown)
        
        # Send condition-specific marker
        if trial['condition'] == 'NP':
            send_marker(win, MARKER_BUNDLE_PRICE_NP)
        elif trial['condition'] == 'LP':
            send_marker(win, MARKER_BUNDLE_PRICE_LP)
        elif trial['condition'] == 'ZP':
            send_marker(win, MARKER_BUNDLE_PRICE_ZP)
        
        kb.clearEvents()
        event.clearEvents()
        price_onset = core.getTime()
        response_deadline = price_onset + PRICE_RESPONSE_TIME
        
        resp_key = None
        rt_ms = None
        response = None
        
        while core.getTime() < response_deadline:
            # Draw stimuli - images + prices
            focal_img_stim.draw()
            tiein_img_stim.draw()
            focal_price_text.draw()
            tiein_price_text.draw()
            fixation.draw()
            win.flip()
            
            # Check for response
            keys = kb.getKeys(keyList=all_resp_keys + ['escape'], waitRelease=False)
            if keys:
                k = keys[0]
                if k.name == 'escape':
                    win.close()
                    core.quit()
                if resp_key is None:
                    resp_key = k.name
                    rt_ms = (k.tDown - price_onset) * 1000  # RT from price onset
                    
                    # Determine response type
                    if resp_key in buy_keys:
                        response = 'BUY'
                        send_marker(win, MARKER_RESPONSE_BUY)
                    else:
                        response = 'NOBUY'
                        send_marker(win, MARKER_RESPONSE_NOBUY)
        
        # If no response, send marker
        if resp_key is None:
            send_marker(win, MARKER_NO_RESPONSE)
        
        # =====================================================================
        # Update tracking
        # =====================================================================
        valid_response = 1 if (rt_ms is not None and rt_ms < 4000) else 0
        
        if response == 'BUY' and valid_response:
            bundles_bought += 1
            # Check if this is the selected bundle
            if is_selected:
                selected_bundle_bought = True
        
        # =====================================================================
        # Log trial to CSV
        # =====================================================================
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                datetime.now().isoformat(timespec='milliseconds'),
                participant_id,
                age,
                response_group,
                t_idx,
                current_block,
                trial['bundle_id'],
                trial['focal_name'],
                trial['tiein_name'],
                trial['condition'],
                trial['focal_price'],
                trial['tiein_price'],
                trial['total_price'],
                ALLOCATION_PER_TRIAL,
                resp_key or '',
                response or '',
                round(rt_ms, 2) if rt_ms is not None else '',
                valid_response,
                is_selected,
                bundles_bought,
            ])
        
        # =====================================================================
        # Block rest screen
        # =====================================================================
        trials_done = t_idx + 1
        if (trials_done % TRIALS_PER_BLOCK == 0) and (trials_done < total_trials):
            completed_block = trials_done // TRIALS_PER_BLOCK
            rest_text.text = (
                f"Block {completed_block} of {N_BLOCKS} completed.\n\n"
                f"You may rest now. Feel free to move and blink.\n\n"
                f"Trials completed: {trials_done} / {total_trials}\n"
                f"Bundles bought so far: {bundles_bought}\n\n"
                f"Press SPACE to continue."
            )
            
            kb.clearEvents()
            event.clearEvents()
            while True:
                rest_text.draw()
                win.flip()
                keys = kb.getKeys(keyList=['space', 'escape'], waitRelease=False)
                if keys:
                    if any(k.name == 'escape' for k in keys):
                        win.close()
                        core.quit()
                    if any(k.name == 'space' for k in keys):
                        kb.clearEvents()
                        event.clearEvents()
                        break
                core.wait(0.01)
    
    # =========================================================================
    # End of experiment - calculate final results
    # =========================================================================
    penalty = calculate_penalty(bundles_bought)
    
    # Penalty description
    if bundles_bought < 20:
        penalty_desc = f"You bought {bundles_bought} bundles (< 20). Penalty: {int(penalty)} ₾"
    elif bundles_bought < 25:
        penalty_desc = f"You bought {bundles_bought} bundles (20-24). Penalty: {int(penalty)} ₾"
    elif bundles_bought < 30:
        penalty_desc = f"You bought {bundles_bought} bundles (25-29). Penalty: {int(penalty)} ₾"
    else:
        penalty_desc = f"You bought {bundles_bought} bundles (≥ 30). No penalty!"
    
    # Selected bundle result
    if selected_bundle_bought:
        bundle_result = f"Congratulations! You bought the selected bundle!\n{selected_bundle_name} will be shipped to you!"
    else:
        bundle_result = f"You did not buy the selected bundle ({selected_bundle_name})."
    
    end_text.text = (
        f"Experiment Complete!\n\n"
        f"Total trials: {total_trials}\n"
        f"Bundles purchased: {bundles_bought}\n\n"
        f"{penalty_desc}\n\n"
        f"{bundle_result}\n\n"
        f"Data saved to:\n{os.path.basename(OUT_CSV)}\n\n"
        f"Press ENTER to exit."
    )
    
    end_text.draw()
    win.flip()
    
    # Log summary to CSV
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([])
        w.writerow(["# SUMMARY"])
        w.writerow(["# Bundles bought", bundles_bought])
        w.writerow(["# Penalty", round(penalty, 2)])
        w.writerow(["# Selected bundle ID", selected_bundle_id])
        w.writerow(["# Selected bundle name", selected_bundle_name])
        w.writerow(["# Selected bundle bought", selected_bundle_bought])
    
    kb.clearEvents()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter', 'escape') for k in keys):
            break
        core.wait(0.01)
    
    # Clean up placeholder images
    temp_dir = os.path.join(BASE_DIR, "temp_images")
    if os.path.exists(temp_dir):
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    
    win.close()
    core.quit()


if __name__ == "__main__":
    main()
