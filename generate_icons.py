"""
Generate PWA icons for ZAIDAN FITNESS mobile app
Run: python generate_icons.py
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # Create static directory if not exists
    os.makedirs('static', exist_ok=True)
    
    # Icon sizes needed for PWA
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Colors
    bg_color = (0, 196, 108)  # Emerald green
    text_color = (255, 255, 255)  # White
    
    print("🎨 Generating PWA icons for ZAIDAN FITNESS...")
    
    for size in sizes:
        # Create image
        img = Image.new('RGB', (size, size), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Add rounded corners for larger icons
        if size >= 192:
            # Create rounded rectangle mask
            mask = Image.new('L', (size, size), 0)
            mask_draw = ImageDraw.Draw(mask)
            radius = size // 8
            mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=255)
            
            # Apply mask
            output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            output.paste(img, (0, 0))
            output.putalpha(mask)
            img = output.convert('RGB')
            draw = ImageDraw.Draw(img)
        
        # Draw "ZF" text for ZAIDAN FITNESS
        try:
            # Try to use a nice font
            font_size = size // 2
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        text = "ZF"
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center text
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - bbox[1]
        
        # Draw text with shadow for depth
        shadow_offset = max(2, size // 100)
        draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0, 100), font=font)
        draw.text((x, y), text, fill=text_color, font=font)
        
        # Add small dumbbell icon at bottom for larger sizes
        if size >= 192:
            # Simple dumbbell shape
            bar_y = int(size * 0.75)
            bar_height = max(4, size // 50)
            bar_width = int(size * 0.4)
            bar_x = (size - bar_width) // 2
            
            # Draw bar
            draw.rectangle(
                [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                fill=text_color
            )
            
            # Draw weights
            weight_size = max(8, size // 30)
            draw.ellipse(
                [(bar_x - weight_size//2, bar_y - weight_size//2), 
                 (bar_x + weight_size//2, bar_y + bar_height + weight_size//2)],
                fill=text_color
            )
            draw.ellipse(
                [(bar_x + bar_width - weight_size//2, bar_y - weight_size//2), 
                 (bar_x + bar_width + weight_size//2, bar_y + bar_height + weight_size//2)],
                fill=text_color
            )
        
        # Save icon
        filename = f'static/icon-{size}.png'
        img.save(filename, 'PNG', optimize=True, quality=95)
        print(f"✅ Created {filename} ({size}x{size})")
    
    # Create favicon
    img_16 = Image.new('RGB', (16, 16), bg_color)
    draw_16 = ImageDraw.Draw(img_16)
    draw_16.text((2, 0), "Z", fill=text_color)
    img_16.save('static/favicon.ico', 'ICO')
    print(f"✅ Created static/favicon.ico (16x16)")
    
    print("\n🎉 All icons generated successfully!")
    print("📱 Your app is ready to install on mobile devices!")
    
except ImportError:
    print("❌ PIL (Pillow) not installed")
    print("📦 Install it: pip install Pillow")
    print("\nOr use online tools to create icons:")
    print("- https://realfavicongenerator.net")
    print("- https://www.pwabuilder.com/imageGenerator")
