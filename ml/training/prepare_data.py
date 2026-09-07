"""
Prepare dataset: convert CVAT XML annotations to YOLO format,
split into train/val/test, and create data.yaml
"""

import xml.etree.ElementTree as ET
import random
import shutil
from pathlib import Path
from loguru import logger


def parse_cvat_xml(xml_path: str) -> list[dict]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Class mapping
    class_map = {}
    for label in root.findall('.//labels/label'):
        class_map[label.find('name').text] = len(class_map)

    images = []
    for img in root.findall('image'):
        name = img.get('name')
        width = int(img.get('width'))
        height = int(img.get('height'))

        boxes = []
        for box in img.findall('box'):
            label_name = box.get('label')
            class_id = class_map[label_name]
            xtl = float(box.get('xtl'))
            ytl = float(box.get('ytl'))
            xbr = float(box.get('xbr'))
            ybr = float(box.get('ybr'))
            boxes.append({
                'class_id': class_id,
                'bbox': [xtl, ytl, xbr, ybr]
            })

        for poly in img.findall('polygon'):
            label_name = poly.get('label')
            class_id = class_map[label_name]
            points_str = poly.get('points')
            xs, ys = [], []
            for pt in points_str.split(';'):
                x, y = pt.split(',')
                xs.append(float(x))
                ys.append(float(y))
            boxes.append({
                'class_id': class_id,
                'bbox': [min(xs), min(ys), max(xs), max(ys)]
            })

        images.append({
            'name': name,
            'width': width,
            'height': height,
            'boxes': boxes
        })

    logger.info(f"Parsed {len(images)} images from XML, classes: {class_map}")
    return images, class_map


def convert_to_yolo_label(boxes: list[dict], img_w: int, img_h: int) -> list[str]:
    lines = []
    for box in boxes:
        x1, y1, x2, y2 = box['bbox']
        x_center = ((x1 + x2) / 2.0) / img_w
        y_center = ((y1 + y2) / 2.0) / img_h
        bw = (x2 - x1) / img_w
        bh = (y2 - y1) / img_h
        lines.append(f"{box['class_id']} {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}")
    return lines


def main():
    # Paths
    xml_path = Path("image/anotasi/annotations.xml")
    src_images = Path("image/data_set")
    output_dir = Path("ml/data/license_plates")

    # Parse annotations
    images, class_map = parse_cvat_xml(str(xml_path))

    # Shuffle for split
    random.seed(42)
    random.shuffle(images)

    n = len(images)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)

    splits = {
        'train': images[:n_train],
        'val': images[n_train:n_train + n_val],
        'test': images[n_train + n_val:]
    }

    # Copy images and create labels
    for split_name, split_images in splits.items():
        img_dir = output_dir / split_name / 'images'
        label_dir = output_dir / split_name / 'labels'
        img_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        for img_data in split_images:
            # Copy image
            src = src_images / img_data['name']
            if not src.exists():
                logger.warning(f"Image not found: {src}")
                continue
            dst_img = img_dir / img_data['name']
            shutil.copy2(src, dst_img)

            # Write YOLO label
            if img_data['boxes']:
                lines = convert_to_yolo_label(img_data['boxes'], img_data['width'], img_data['height'])
                label_path = label_dir / f"{Path(img_data['name']).stem}.txt"
                label_path.write_text('\n'.join(lines) + '\n')

        logger.info(f"{split_name}: {len(split_images)} images")

    # Create data.yaml
    yaml_path = output_dir / "data.yaml"
    yaml_content = f"""path: {output_dir.absolute()}
train: train/images
val: val/images
test: test/images

names:
"""
    for i, name in enumerate(class_map.keys()):
        yaml_content += f"  {i}: {name}\n"

    yaml_path.write_text(yaml_content)
    logger.success(f"data.yaml created at {yaml_path}")
    logger.success(f"Dataset ready! Total: {n} images | Train: {n_train} | Val: {n_val} | Test: {n - n_train - n_val}")


if __name__ == "__main__":
    main()
