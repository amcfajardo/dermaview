
import cv2
import numpy as np
import sys
from pathlib import Path

DISCLAIMER = "Educational visualization only; not a medical diagnosis or guaranteed treatment result."

COLORS = {
    "red": (35, 55, 220),
    "orange": (0, 145, 255),
    "green": (70, 165, 70),
    "blue": (210, 130, 35),
    "purple": (185, 85, 175),
    "cyan": (190, 150, 35),
    "navy": (78, 48, 25),
    "text": (45, 45, 45),
    "muted": (100, 100, 100),
    "panel": (255, 255, 255),
    "line": (220, 224, 230),
}


def fail(message, code=1):
    print(message)
    sys.exit(code)


def read_image(input_path):
    img = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if img is None:
        fail("Image not found or unsupported image format")
    return img


def save_image(output_path, img):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(output_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        fail("Failed to save output image")


def resize_for_processing(img, max_size=1200):
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_size:
        return img
    scale = max_size / float(longest)
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def clamp_intensity(value, default=1.0):
    try:
        value = float(value)
    except Exception:
        value = default
    return float(np.clip(value, 0.35, 1.50))


def detect_face_bbox(img):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        cascade = cv2.CascadeClassifier(cascade_path)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(max(50, w//8), max(50, h//8)))
    except Exception:
        faces = []
    if len(faces) > 0:
        x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        pad_x, pad_y = int(fw * 0.22), int(fh * 0.34)
        x = max(0, x - pad_x)
        y = max(0, y - pad_y)
        fw = min(w - x, fw + pad_x * 2)
        fh = min(h - y, fh + int(pad_y * 1.65))
        return (x, y, fw, fh)
    # fallback centered head/face estimate
    return (int(w * 0.23), int(h * 0.10), int(w * 0.54), int(h * 0.68))


def skin_mask_bgr(img, bbox=None):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    mask_hsv = cv2.inRange(hsv, np.array([0, 14, 32]), np.array([35, 235, 255]))
    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 126, 68]), np.array([255, 188, 154]))
    mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
    if bbox is not None:
        face = face_oval_mask(np.zeros(img.shape[:2], np.uint8), bbox, blur=0)
        mask = cv2.bitwise_and(mask, face)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    if cv2.countNonZero(mask) < img.shape[0] * img.shape[1] * 0.015:
        h, w = img.shape[:2]
        if bbox is None:
            bbox = detect_face_bbox(img)
        mask = face_oval_mask(np.zeros((h, w), np.uint8), bbox, blur=0)
    return cv2.GaussianBlur(mask, (35, 35), 0)


def face_oval_mask(mask, bbox, blur=21):
    x, y, w, h = bbox
    center = (int(x + w * 0.50), int(y + h * 0.52))
    axes = (max(1, int(w * 0.43)), max(1, int(h * 0.50)))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    if blur:
        k = blur if blur % 2 else blur + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def ellipse_mask(shape, center, axes, blur=0):
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, (int(center[0]), int(center[1])), (max(1, int(axes[0])), max(1, int(axes[1]))), 0, 0, 360, 255, -1)
    if blur:
        k = blur if blur % 2 else blur + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def blend(original, processed, mask, strength=1.0):
    f = np.clip((mask.astype(np.float32) / 255.0) * strength, 0, 1)
    f3 = cv2.merge([f, f, f])
    return np.clip(processed.astype(np.float32) * f3 + original.astype(np.float32) * (1 - f3), 0, 255).astype(np.uint8)


def protect_features_mask(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 45, 110)
    dark = cv2.inRange(gray, 0, 70)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lip1 = cv2.inRange(hsv, np.array([0, 25, 35]), np.array([18, 195, 245]))
    lip2 = cv2.inRange(hsv, np.array([155, 25, 35]), np.array([180, 195, 245]))
    mask = cv2.bitwise_or(edges, dark)
    mask = cv2.bitwise_or(mask, cv2.bitwise_or(lip1, lip2))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    return cv2.GaussianBlur(mask, (21, 21), 0)


def gentle_sharpen(img, amount=0.06):
    blur = cv2.GaussianBlur(img, (0, 0), 1)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)


def enhance_lab(img, l_alpha=1.04, l_beta=4, a_smooth=0.06):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.convertScaleAbs(l, alpha=l_alpha, beta=l_beta)
    a = cv2.addWeighted(a, 1 - a_smooth, cv2.GaussianBlur(a, (0, 0), 3), a_smooth, 0)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def put_text(img, text, pos, scale=0.5, color=(45,45,45), thick=1):
    cv2.putText(img, str(text), pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def wrap_lines(text, max_chars=45):
    words = str(text).split()
    lines, cur = [], ''
    for word in words:
        if len(cur) + len(word) + 1 <= max_chars:
            cur = (cur + ' ' + word).strip()
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines


def put_wrapped(img, text, x, y, max_chars=45, scale=0.42, color=(45,45,45), line_h=18, max_lines=3):
    for line in wrap_lines(text, max_chars)[:max_lines]:
        put_text(img, line, (x, y), scale, color, 1)
        y += line_h
    return y


def rounded_rect(img, pt1, pt2, color, border=None, radius=14, thickness=-1):
    # Simple rectangle fallback with antialiased borders; OpenCV lacks native rounded rect.
    cv2.rectangle(img, pt1, pt2, color, thickness, cv2.LINE_AA)
    if border is not None:
        cv2.rectangle(img, pt1, pt2, border, 1, cv2.LINE_AA)


def draw_dashed_ellipse(img, center, axes, color, thickness=1, dash_deg=5, gap_deg=8):
    start = 0
    while start < 360:
        end = min(start + dash_deg, 360)
        cv2.ellipse(img, (int(center[0]), int(center[1])), (max(1, int(axes[0])), max(1, int(axes[1]))), 0, start, end, color, thickness, cv2.LINE_AA)
        start += dash_deg + gap_deg


def draw_soft_area(img, mask, color, alpha=0.045):
    overlay = img.copy()
    overlay[mask > 0] = color
    return cv2.addWeighted(overlay, alpha, img, 1-alpha, 0)


def draw_badge(img, center, text, color, r=13):
    x, y = int(center[0]), int(center[1])
    cv2.circle(img, (x, y), r, color, -1, cv2.LINE_AA)
    cv2.circle(img, (x, y), r, (255,255,255), 2, cv2.LINE_AA)
    tw = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 2)[0][0]
    put_text(img, text, (x - tw//2, y + 5), 0.45, (255,255,255), 2)


def severity_label(score):
    if score < 18: return 'Low'
    if score < 40: return 'Mild'
    if score < 65: return 'Moderate'
    return 'High'


def create_before_after_report(original, processed, title, findings, recommendations=None):
    original = resize_for_processing(original, 900)
    processed = cv2.resize(processed, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_AREA)
    h, w = original.shape[:2]
    panel_h = 250
    gap = 18
    top_h = 58
    out_w = w*2 + gap + 48
    out_h = top_h + h + panel_h + 38
    canvas = np.full((out_h, out_w, 3), 248, dtype=np.uint8)
    cv2.rectangle(canvas, (0,0), (out_w, top_h), COLORS['navy'], -1)
    tw = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)[0][0]
    put_text(canvas, title, ((out_w-tw)//2, 38), 0.85, (255,255,255), 2)
    x1, y1 = 24, top_h + 16
    x2 = x1 + w + gap
    canvas[y1:y1+h, x1:x1+w] = original
    canvas[y1:y1+h, x2:x2+w] = processed
    cv2.rectangle(canvas, (x1,y1), (x1+w,y1+h), (225,225,225), 1)
    cv2.rectangle(canvas, (x2,y1), (x2+w,y1+h), (225,225,225), 1)
    # labels below image, not blocking face
    for label, xx in [('BEFORE', x1), ('AFTER', x2)]:
        cv2.rectangle(canvas, (xx+14, y1+h-42), (xx+120, y1+h-12), (20,20,20), -1, cv2.LINE_AA)
        put_text(canvas, label, (xx+31, y1+h-20), 0.55, (255,255,255), 2)
    py = y1 + h + 24
    rounded_rect(canvas, (24, py), (out_w-24, out_h-20), (255,255,255), (220,225,232))
    put_text(canvas, 'EDUCATIONAL VISUALIZATION FINDINGS', (48, py+32), 0.58, COLORS['navy'], 2)
    col_w = (out_w-96)//2
    fx = 48
    fy = py + 64
    for i, line in enumerate(findings[:4]):
        yy = fy + i*36
        cv2.circle(canvas, (fx+8, yy-2), 8, COLORS['green'], -1, cv2.LINE_AA)
        put_text(canvas, '✓', (fx+3, yy+3), 0.35, (255,255,255), 1)
        put_wrapped(canvas, line, fx+24, yy+3, 58, 0.42, COLORS['text'], 16, 2)
    rx = 48 + col_w + 28
    put_text(canvas, 'RECOMMENDED USE', (rx, py+32), 0.58, (40,100,45), 2)
    if recommendations is None:
        recommendations = ['Use as visual guide only', 'Consult a licensed professional for actual evaluation', 'Compare before and after output with original image']
    for i, line in enumerate(recommendations[:4]):
        yy = fy + i*36
        cv2.circle(canvas, (rx+8, yy-2), 8, COLORS['orange'], -1, cv2.LINE_AA)
        put_wrapped(canvas, line, rx+24, yy+3, 48, 0.42, COLORS['text'], 16, 2)
    put_text(canvas, 'Disclaimer: ' + DISCLAIMER, (48, out_h-34), 0.38, COLORS['muted'], 1)
    return canvas

def face_regions(shape, bbox):
    x,y,w,h = bbox
    raw = [
        (1,'Forehead Area','forehead across the upper face','redness/acne-like signals and uneven tone',(35,55,220),(x+w*.50,y+h*.20),(w*.34,h*.10)),
        (2,'Left Cheek Area','left mid-to-lower cheek','pigmentation/dark-spot-like signals and uneven tone',(0,135,255),(x+w*.30,y+h*.52),(w*.17,h*.22)),
        (3,'Right Cheek Area','right mid-to-lower cheek','pigmentation/dark-spot-like signals and uneven tone',(70,165,70),(x+w*.70,y+h*.52),(w*.17,h*.22)),
        (4,'Undereye Area','both left and right under-eye zones','dark-circle/shadowing-like signals',(185,85,175),(x+w*.50,y+h*.36),(w*.31,h*.055)),
        (5,'Nose Area (T-Zone)','nose bridge, sides, and tip','visible pores/blackhead-like signals',(210,130,35),(x+w*.50,y+h*.47),(w*.095,h*.21)),
        (6,'Chin Area','central chin and lower jawline','texture unevenness / blemish-like signals',(190,150,35),(x+w*.50,y+h*.78),(w*.24,h*.10)),
    ]
    face = face_oval_mask(np.zeros(shape[:2], np.uint8), bbox, blur=0)
    regs=[]
    for rid,name,zone,concern,color,center,axes in raw:
        mask = cv2.bitwise_and(ellipse_mask(shape, center, axes, blur=0), face)
        regs.append({'id':rid,'name':name,'zone':zone,'concern':concern,'color':color,'center':center,'axes':axes,'mask':mask})
    return regs


def assess_region(region, hsv, lab, gray, skin_mask):
    mask = cv2.bitwise_and(region['mask'], skin_mask)
    if cv2.countNonZero(mask) < 50: mask = region['mask']
    pix = max(1, cv2.countNonZero(mask))
    _, a, _ = cv2.split(lab)
    skin_pix = max(1, cv2.countNonZero(skin_mask))
    a_mean = cv2.mean(a, mask=skin_mask)[0]
    skin_mean = cv2.mean(gray, mask=skin_mask)[0]
    red_lab = cv2.inRange(a, int(max(134, a_mean + 7)), 210)
    red_hsv = cv2.bitwise_or(cv2.inRange(hsv,np.array([0,36,45]),np.array([18,255,255])), cv2.inRange(hsv,np.array([155,36,45]),np.array([180,255,255])))
    red = cv2.bitwise_and(cv2.bitwise_or(red_lab, red_hsv), mask)
    dark = cv2.bitwise_and(cv2.inRange(gray,0,int(max(40,skin_mean-20))), mask)
    lap = cv2.Laplacian(gray,cv2.CV_64F); vals=lap[mask>0]; texture=min(100.0, (float(np.var(vals)) if vals.size else 0)/3.2)
    lum = cv2.mean(gray, mask=mask)[0]; shadow=min(100.0, max(0, skin_mean-lum)*2.8)
    red_pct=cv2.countNonZero(red)/pix*100.0; dark_pct=cv2.countNonZero(dark)/pix*100.0
    name=region['name'].lower()
    if 'forehead' in name: score=min(100, red_pct*2.4+dark_pct*1.0+texture*.10); primary='redness/acne-like signals'
    elif 'cheek' in name: score=min(100, dark_pct*2.0+red_pct*1.2+texture*.10); primary='pigmentation/dark-spot-like signals'
    elif 'undereye' in name: score=min(100, shadow+dark_pct*1.3+red_pct*.4); primary='dark-circle/shadowing-like signals'
    elif 'nose' in name: score=min(100, texture*.45+dark_pct*1.1+red_pct*.5); primary='pores/blackhead-like signals'
    elif 'chin' in name: score=min(100, texture*.38+red_pct*1.1+dark_pct*.8); primary='texture unevenness / blemish-like signals'
    else: score=min(100, red_pct+dark_pct+texture*.2); primary=region['concern']
    return {'score':float(score),'severity':severity_label(score),'primary':primary,'red_pct':red_pct,'dark_pct':dark_pct,'texture':texture,'shadow':shadow}


def build_assessment_canvas(original, regions, assessments):
    # portrait-style report: large photo at top, professional bottom findings.
    img = resize_for_processing(original, 980)
    # Scale region geometry to resized image
    sx = img.shape[1] / original.shape[1]; sy = img.shape[0] / original.shape[0]
    scaled=[]
    for r in regions:
        rr=r.copy(); rr['center']=(r['center'][0]*sx, r['center'][1]*sy); rr['axes']=(r['axes'][0]*sx, r['axes'][1]*sy); rr['mask']=cv2.resize(r['mask'], (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST); scaled.append(rr)
    h,w = img.shape[:2]
    title_h = 64
    panel_h = 470 if w >= 700 else 540
    canvas = np.full((title_h+h+panel_h, w, 3), 248, dtype=np.uint8)
    cv2.rectangle(canvas,(0,0),(w,title_h),COLORS['navy'],-1)
    title='GENERAL SKIN ASSESSMENT'
    tw=cv2.getTextSize(title,cv2.FONT_HERSHEY_SIMPLEX,0.95,2)[0][0]
    put_text(canvas,title,((w-tw)//2,42),0.95,(255,255,255),2)
    photo = img.copy()
    # Draw thin zones and soft overlays; number badges are outside the face, connected with lines.
    for r in scaled:
        photo = draw_soft_area(photo, r['mask'], r['color'], 0.045)
        draw_dashed_ellipse(photo, r['center'], r['axes'], r['color'], thickness=1, dash_deg=5, gap_deg=9)
    # Badge positions outside or near perimeter, not centered on facial features.
    badge_pos = {
        1:(int(w*0.77), int(h*0.18)), 2:(int(w*0.16), int(h*0.46)), 3:(int(w*0.84), int(h*0.46)),
        4:(int(w*0.16), int(h*0.34)), 5:(int(w*0.84), int(h*0.34)), 6:(int(w*0.78), int(h*0.80))
    }
    for r in scaled:
        bp=badge_pos[r['id']]; cp=(int(r['center'][0]), int(r['center'][1]))
        cv2.line(photo, bp, cp, r['color'], 1, cv2.LINE_AA)
        draw_badge(photo, bp, str(r['id']), r['color'], r=14)
    canvas[title_h:title_h+h,0:w]=photo
    y0=title_h+h+18; margin=24
    rounded_rect(canvas,(margin,y0),(w-margin,title_h+h+panel_h-18),(255,255,255),(218,224,232))
    put_text(canvas,'AREA-BY-AREA EDUCATIONAL FINDINGS',(margin+18,y0+34),0.62,COLORS['navy'],2)
    col1=margin+22; col2=w//2+8; row_h=82; sy0=y0+70
    for i,r in enumerate(scaled):
        x = col1 if i<3 else col2
        y = sy0 + (i%3)*row_h
        a=assessments[r['id']]; color=r['color']
        cv2.circle(canvas,(x+12,y-2),11,color,-1,cv2.LINE_AA); put_text(canvas,str(r['id']),(x+7,y+3),0.38,(255,255,255),1)
        put_text(canvas,r['name'].upper(),(x+30,y-5),0.44,color,2)
        put_wrapped(canvas,'Zone: '+r['zone']+'.',x+30,y+16,44,0.37,COLORS['muted'],15,1)
        put_wrapped(canvas,f"Finding: {a['severity']} {a['primary']} observed.",x+30,y+34,44,0.37,COLORS['text'],15,2)
        bx = x+310 if w<850 else x+380
        cv2.rectangle(canvas,(bx,y-22),(bx+78,y+3),(247,250,252),-1,cv2.LINE_AA); cv2.rectangle(canvas,(bx,y-22),(bx+78,y+3),color,1,cv2.LINE_AA)
        put_text(canvas,a['severity'],(bx+10,y-5),0.34,color,1)
    sum_y = sy0 + 3*row_h + 18
    cv2.line(canvas,(margin+18,sum_y-18),(w-margin-18,sum_y-18),(220,225,230),1,cv2.LINE_AA)
    put_text(canvas,'OVERALL SUMMARY',(margin+18,sum_y+8),0.53,COLORS['navy'],2)
    metrics=[('Redness / acne-like',np.mean([assessments[1]['red_pct'],assessments[2]['red_pct'],assessments[3]['red_pct']])*2.4,COLORS['red']),('Pigmentation / dark spots',np.mean([assessments[2]['dark_pct'],assessments[3]['dark_pct']])*2.0,COLORS['orange']),('Texture / pores',np.mean([assessments[5]['texture'],assessments[6]['texture']]),COLORS['blue']),('Undereye shadowing',assessments[4]['shadow'],COLORS['purple'])]
    bx=margin+230; bw=max(110,w//5)
    for j,(labtxt,score,color) in enumerate(metrics):
        yy=sum_y+34+j*24; score=float(np.clip(score,0,100))
        put_text(canvas,labtxt,(margin+32,yy+4),0.38,COLORS['text'],1)
        cv2.rectangle(canvas,(bx,yy-6),(bx+bw,yy+4),(234,237,241),-1,cv2.LINE_AA); cv2.rectangle(canvas,(bx,yy-6),(bx+int(bw*score/100),yy+4),color,-1,cv2.LINE_AA)
        put_text(canvas,f'{int(round(score))}%',(bx+bw+10,yy+4),0.36,COLORS['muted'],1)
    rx=w//2+18
    put_text(canvas,'RECOMMENDED VISUALIZATIONS',(rx,sum_y+8),0.53,(40,100,45),2)
    recs=['CO2 Laser + Dermapen','PICO Carbon Laser','Diamond Peel Facial','Undereye + Lip Filler']
    for j,rec in enumerate(recs):
        yy=sum_y+34+j*24; cv2.circle(canvas,(rx+8,yy),8,COLORS['green'],-1,cv2.LINE_AA); put_text(canvas,'✓',(rx+3,yy+5),0.35,(255,255,255),1); put_text(canvas,rec,(rx+24,yy+4),0.38,COLORS['text'],1)
    put_text(canvas,'Disclaimer: '+DISCLAIMER,(margin+18,title_h+h+panel_h-34),0.36,COLORS['muted'],1)
    return canvas


def process_general_skin_assessment(input_path, output_path):
    original=resize_for_processing(read_image(input_path), 1200)
    bbox=detect_face_bbox(original); hsv=cv2.cvtColor(original,cv2.COLOR_BGR2HSV); lab=cv2.cvtColor(original,cv2.COLOR_BGR2LAB); gray=cv2.cvtColor(original,cv2.COLOR_BGR2GRAY); skin=skin_mask_bgr(original,bbox)
    regions=face_regions(original.shape,bbox); assessments={r['id']:assess_region(r,hsv,lab,gray,skin) for r in regions}
    canvas=build_assessment_canvas(original,regions,assessments)
    save_image(output_path,canvas)
    print('General Skin Assessment professional area report saved:', output_path); print(DISCLAIMER); sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv)<3: fail('Usage: python process_general_skin_assessment.py input output')
    process_general_skin_assessment(sys.argv[1], sys.argv[2])
