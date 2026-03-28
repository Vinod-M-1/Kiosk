def map_ocr_regions(ocr_data, screen_width, screen_height):
    """
    Groups OCR bounding boxes into distinct 3x3 spatial regions to dramatically 
    improve LLM comprehension and reduce token hallucination.
    """
    if not ocr_data:
        return "The screen appears to be empty."

    regions = {"Top-Left": [], "Top-Center": [], "Top-Right": [],
               "Center-Left": [], "Center": [], "Center-Right": [],
               "Bottom-Left": [], "Bottom-Center": [], "Bottom-Right": []}

    for bbox, text, prob in ocr_data:
        if prob < 0.4:
            continue
            
        # Calculate center
        center_x = (bbox[0][0] + bbox[2][0]) / 2
        center_y = (bbox[0][1] + bbox[2][1]) / 2
        
        # Horizontal bucket
        if center_x < screen_width / 3:
            h_region = "Left"
        elif center_x < 2 * screen_width / 3:
            h_region = "Center"
        else:
            h_region = "Right"
            
        # Vertical bucket
        if center_y < screen_height / 3:
            v_region = "Top"
        elif center_y < 2 * screen_height / 3:
            v_region = "Center"
        else:
            v_region = "Bottom"
            
        region_key = f"{v_region}-{h_region}"
        if v_region == "Center" and h_region == "Center":
            region_key = "Center"
            
        regions[region_key].append(text)
        
    # Compile the final spatial map report
    mapped_text = []
    for region, texts in regions.items():
        if texts:
            mapped_text.append(f"[{region}]: " + " | ".join(texts))
            
    return "\n".join(mapped_text)
