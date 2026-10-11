"""Catalog for the built-in demo store ("CartMart").

CartMind needs a real website that Playwright can drive without bypassing anyone's security
or terms of service, so the MVP ships its own small store. The same catalog backs the search
tool, so what the agent researches is exactly what the browser later finds on the site.
"""

from copy import deepcopy
from typing import Any

SOURCE = "cartmart"

_P = lambda **kw: kw  # noqa: E731

CATALOG: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ laptops
    _P(id="lap-001", name="ASUS Vivobook 15 X1504", brand="ASUS", category="laptop", price=47990, rating=4.4,
       review_count=2310, available=True,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="Intel Core i5-1235U", battery_hours=9,
                  display="15.6\" FHD IPS", weight_kg=1.7, gpu="Intel Iris Xe"),
       features=["Backlit keyboard", "Fingerprint reader", "Fast charging"],
       reviews=["Great for coding, VS Code and Docker run smoothly.", "Battery lasts a full workday.",
                "Screen is decent but not very bright."]),
    _P(id="lap-002", name="Lenovo IdeaPad Slim 3 Ryzen 5", brand="Lenovo", category="laptop", price=49490, rating=4.2,
       review_count=1840, available=True,
       specs=dict(ram_gb=16, storage_gb=1024, storage_type="SSD", processor="AMD Ryzen 5 7520U", battery_hours=8,
                  display="15.6\" FHD IPS", weight_kg=1.62, gpu="AMD Radeon 610M"),
       features=["1TB SSD", "Dolby Audio", "Privacy shutter"],
       reviews=["Huge storage for the price.", "Good display and keyboard.", "Battery is just average."]),
    _P(id="lap-003", name="HP 15s Ryzen 5 Everyday", brand="HP", category="laptop", price=44990, rating=4.5,
       review_count=3120, available=True,
       specs=dict(ram_gb=8, storage_gb=512, storage_type="SSD", processor="AMD Ryzen 5 5500U", battery_hours=7,
                  display="15.6\" FHD", weight_kg=1.69, gpu="AMD Radeon Graphics"),
       features=["Upgradable RAM", "Thin bezels"],
       reviews=["Reliable daily driver.", "8GB RAM is limiting when many tabs are open."]),
    _P(id="lap-004", name="Acer Aspire 5 Core i5 12th Gen", brand="Acer", category="laptop", price=46999, rating=4.3,
       review_count=1560, available=True,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="Intel Core i5-1235U", battery_hours=10,
                  display="15.6\" FHD IPS", weight_kg=1.76, gpu="Intel Iris Xe"),
       features=["Wi-Fi 6", "Backlit keyboard", "Metal lid"],
       reviews=["Excellent battery life.", "Good keyboard for long coding sessions.", "Speakers are weak."]),
    _P(id="lap-005", name="Dell Inspiron 14 Core i5", brand="Dell", category="laptop", price=52990, rating=4.1,
       review_count=980, available=True,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="Intel Core i5-1335U", battery_hours=9,
                  display="14\" FHD+", weight_kg=1.54, gpu="Intel Iris Xe"),
       features=["Lightweight", "Backlit keyboard"],
       reviews=["Light and portable.", "A bit pricey for the specs."]),
    _P(id="lap-006", name="Lenovo LOQ Gaming Ryzen 5 RTX 3050", brand="Lenovo", category="laptop", price=62990,
       rating=4.4, review_count=2750, available=True,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="AMD Ryzen 5 6600H", battery_hours=5,
                  display="15.6\" FHD 144Hz", weight_kg=2.4, gpu="NVIDIA RTX 3050 6GB"),
       features=["144Hz display", "RTX 3050", "RGB keyboard"],
       reviews=["Excellent performance for compiling and gaming.", "Battery drains quickly.", "Heavy."]),
    _P(id="lap-007", name="ASUS TUF Gaming F15 i5 RTX 2050", brand="ASUS", category="laptop", price=58990, rating=4.3,
       review_count=1620, available=True,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="Intel Core i5-11400H", battery_hours=6,
                  display="15.6\" FHD 144Hz", weight_kg=2.3, gpu="NVIDIA RTX 2050"),
       features=["MIL-STD durability", "144Hz display"],
       reviews=["Sturdy build.", "Runs hot under load."]),
    _P(id="lap-008", name="Samsung Galaxy Book3 OLED", brand="Samsung", category="laptop", price=55990, rating=4.0,
       review_count=410, available=True,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="Intel Core i5-1335U", battery_hours=11,
                  display="15.6\" FHD AMOLED", weight_kg=1.55, gpu="Intel Iris Xe"),
       features=["AMOLED display", "Very light", "Great battery"],
       reviews=["The AMOLED screen is gorgeous.", "Battery is excellent.", "Expensive for the performance."]),
    _P(id="lap-009", name="HP Pavilion 14 Core i5 16GB", brand="HP", category="laptop", price=51990, rating=4.2,
       review_count=1330, available=False,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="Intel Core i5-1335U", battery_hours=9,
                  display="14\" FHD IPS", weight_kg=1.4, gpu="Intel Iris Xe"),
       features=["Alexa built-in", "Thin and light"],
       reviews=["Premium feel.", "Often out of stock."]),
    _P(id="lap-010", name="Lenovo V15 Ryzen 3 8GB", brand="Lenovo", category="laptop", price=31990, rating=3.9,
       review_count=2210, available=True,
       specs=dict(ram_gb=8, storage_gb=256, storage_type="SSD", processor="AMD Ryzen 3 7320U", battery_hours=7,
                  display="15.6\" FHD", weight_kg=1.7, gpu="AMD Radeon Graphics"),
       features=["Budget friendly"], reviews=["Fine for browsing and documents.", "Too little storage."]),
    _P(id="lap-011", name="MSI Modern 14 Ryzen 7 16GB", brand="MSI", category="laptop", price=48990, rating=4.3,
       review_count=640, available=True,
       specs=dict(ram_gb=16, storage_gb=512, storage_type="SSD", processor="AMD Ryzen 7 7730U", battery_hours=12,
                  display="14\" FHD IPS", weight_kg=1.4, gpu="AMD Radeon Graphics"),
       features=["8-core CPU", "Long battery", "Light"],
       reviews=["Fastest CPU in this price range.", "Battery easily lasts all day.", "Fans get audible under load."]),
    _P(id="lap-012", name="Apple MacBook Air M2 8GB", brand="Apple", category="laptop", price=89990, rating=4.7,
       review_count=5200, available=True,
       specs=dict(ram_gb=8, storage_gb=256, storage_type="SSD", processor="Apple M2", battery_hours=15,
                  display="13.6\" Liquid Retina", weight_kg=1.24, gpu="Apple 8-core GPU"),
       features=["Fanless", "Best-in-class battery"],
       reviews=["Superb build and battery.", "Expensive upgrades."]),
    # --------------------------------------------------------------- headphones
    _P(id="hp-001", name="Sony WH-CH720N Wireless ANC", brand="Sony", category="headphones", price=4799, rating=4.4,
       review_count=8420, available=True,
       specs=dict(anc=True, battery_hours=35, type="over-ear", bluetooth="5.2", driver_mm=30, weight_g=192),
       features=["Active noise cancelling", "Multipoint", "Lightweight"],
       reviews=["ANC is excellent at this price.", "35 hours of battery is real.", "Plastic build."]),
    _P(id="hp-002", name="boAt Rockerz 551 ANC", brand="boAt", category="headphones", price=2999, rating=4.0,
       review_count=12650, available=True,
       specs=dict(anc=True, battery_hours=100, type="over-ear", bluetooth="5.3", driver_mm=40, weight_g=250),
       features=["100-hour battery", "ANC", "Low-latency mode"],
       reviews=["Battery lasts forever.", "ANC is weak compared to premium brands.", "Bass heavy."]),
    _P(id="hp-003", name="JBL Tune 770NC", brand="JBL", category="headphones", price=4999, rating=4.3, review_count=5140,
       available=True,
       specs=dict(anc=True, battery_hours=70, type="over-ear", bluetooth="5.3", driver_mm=40, weight_g=234),
       features=["Adaptive ANC", "70-hour battery", "Foldable"],
       reviews=["Balanced, punchy sound.", "ANC is decent.", "Great battery."]),
    _P(id="hp-004", name="Soundcore Space One ANC", brand="Anker", category="headphones", price=7499, rating=4.5,
       review_count=3300, available=True,
       specs=dict(anc=True, battery_hours=40, type="over-ear", bluetooth="5.3", driver_mm=40, weight_g=265),
       features=["Hi-Res audio", "Strong ANC", "Companion app"],
       reviews=["Best ANC under 10k.", "Slightly over budget for many."]),
    _P(id="hp-005", name="Realme Buds Wireless 3", brand="Realme", category="headphones", price=1799, rating=4.2,
       review_count=21000, available=True,
       specs=dict(anc=False, battery_hours=40, type="neckband", bluetooth="5.0", driver_mm=13.6, weight_g=40),
       features=["Neckband", "Fast charge"], reviews=["Great value.", "No ANC."]),
    _P(id="hp-006", name="Noise Two Wireless ANC", brand="Noise", category="headphones", price=3499, rating=3.9,
       review_count=2600, available=True,
       specs=dict(anc=True, battery_hours=25, type="over-ear", bluetooth="5.3", driver_mm=40, weight_g=225),
       features=["ANC", "Foldable"], reviews=["Okay ANC for the price.", "Battery average."]),
    _P(id="hp-007", name="OnePlus Nord Buds 3 Pro", brand="OnePlus", category="headphones", price=2999, rating=4.1,
       review_count=7800, available=True,
       specs=dict(anc=True, battery_hours=44, type="in-ear", bluetooth="5.3", driver_mm=12.4, weight_g=45),
       features=["49dB ANC", "IP55"], reviews=["Strong ANC in tiny buds.", "Comfortable."]),
    _P(id="hp-008", name="Sennheiser Momentum 4", brand="Sennheiser", category="headphones", price=24990, rating=4.6,
       review_count=1200, available=True,
       specs=dict(anc=True, battery_hours=60, type="over-ear", bluetooth="5.2", driver_mm=42, weight_g=293),
       features=["Premium sound", "Adaptive ANC"], reviews=["Superb sound.", "Pricey."]),
    _P(id="hp-009", name="Zebronics Zeb-Thunder", brand="Zebronics", category="headphones", price=999, rating=3.8,
       review_count=14500, available=True,
       specs=dict(anc=False, battery_hours=60, type="over-ear", bluetooth="5.0", driver_mm=40, weight_g=210),
       features=["Budget"], reviews=["Good for the price.", "No ANC."]),
    # ------------------------------------------------------------------- phones
    _P(id="ph-001", name="Redmi Note 13 Pro 5G 8GB/256GB", brand="Xiaomi", category="phone", price=24999, rating=4.3,
       review_count=9100, available=True,
       specs=dict(ram_gb=8, storage_gb=256, battery_mah=5100, camera_mp=200, display="6.67\" AMOLED 120Hz"),
       features=["200MP camera", "67W charging"], reviews=["Camera is excellent for the price.", "Bloatware."]),
    _P(id="ph-002", name="Samsung Galaxy M35 5G 8GB/128GB", brand="Samsung", category="phone", price=19999, rating=4.2,
       review_count=6400, available=True,
       specs=dict(ram_gb=8, storage_gb=128, battery_mah=6000, camera_mp=50, display="6.6\" sAMOLED 120Hz"),
       features=["6000mAh battery"], reviews=["Battery lasts two days.", "Average cameras."]),
    _P(id="ph-003", name="Nothing Phone (2a) 8GB/128GB", brand="Nothing", category="phone", price=23999, rating=4.4,
       review_count=7200, available=True,
       specs=dict(ram_gb=8, storage_gb=128, battery_mah=5000, camera_mp=50, display="6.7\" AMOLED 120Hz"),
       features=["Glyph interface", "Clean software"], reviews=["Smooth software.", "Unique design."]),
    _P(id="ph-004", name="iQOO Z9 5G 8GB/256GB", brand="iQOO", category="phone", price=21999, rating=4.3,
       review_count=5300, available=True,
       specs=dict(ram_gb=8, storage_gb=256, battery_mah=6000, camera_mp=50, display="6.67\" AMOLED 120Hz"),
       features=["Dimensity 7200", "80W charging"], reviews=["Great performance.", "Camera is average."]),
]

_overrides: dict[str, dict[str, Any]] = {}


def set_override(product_id: str, **fields: Any) -> None:
    """Change a product at runtime (used by tests to simulate price changes / stock-outs)."""
    _overrides.setdefault(product_id, {}).update(fields)


def clear_overrides() -> None:
    _overrides.clear()


def _effective(raw: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(raw)
    item.update(_overrides.get(raw["id"], {}))
    item["currency"] = "INR"
    item["source"] = SOURCE
    return item


def all_products() -> list[dict[str, Any]]:
    return [_effective(p) for p in CATALOG]


def get_product(product_id: str) -> dict[str, Any] | None:
    for p in CATALOG:
        if p["id"] == product_id:
            return _effective(p)
    return None
