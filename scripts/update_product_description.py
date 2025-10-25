import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from store.models import Product

# New compelling product description
new_description = """Transform your 3D printing experience with our Premium Recycled Mixed Filament – where sustainability meets exceptional quality.

🌿 **Eco-Friendly Innovation**
Crafted from 100% recycled plastic waste, this filament proves that environmental responsibility doesn't mean compromising on performance. Each spool represents plastic saved from landfills and oceans, transformed into something extraordinary.

🔬 **Laboratory-Tested Quality**
Don't let the "recycled" label fool you. Our filament undergoes rigorous scientific testing to ensure:
• Consistent diameter tolerance (±0.03mm)
• Optimal extrusion temperature range
• Minimal moisture absorption
• Excellent layer adhesion
• Vibrant, lasting colours

✨ **Perfect for Every Project**
Whether you're prototyping, creating functional parts, or bringing artistic visions to life, our mixed filament delivers reliable results print after print. The unique blend creates interesting visual effects that add character to your creations.

💚 **Print with Purpose**
Every spool purchased directly supports the circular economy and helps fund our plastic collection initiatives. You're not just buying filament – you're investing in a cleaner planet.

**Specifications:**
• Material: Recycled PLA/PET blend
• Weight: 1kg spool
• Diameter: 1.75mm
• Print Temperature: 200-220°C
• Bed Temperature: 50-60°C
• Compatible with most FDM 3D printers

**Why Choose KnightCycle Filament?**
Unlike standard filament, ours comes with a story. Each spool is traceable back to the community members who helped collect the plastic waste. You're part of a movement that's actively cleaning up our environment while creating amazing 3D prints.

Join the recycling revolution. Print sustainably. Create responsibly.

---
*Note: Due to the recycled nature of this product, slight colour variations between batches add to the unique character of each spool. We see this as a feature, not a flaw!*"""

# Update the product
product = Product.objects.get(slug='test-product-mixed-filament')
product.description = new_description
product.save()

print("✅ Product description updated successfully!")
print(f"\nUpdated: {product.name}")
print(f"Price: £{product.price}")
print("\nNew Description Preview:")
print(new_description[:300] + "...")
