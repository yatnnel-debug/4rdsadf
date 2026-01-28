
import logging
from lottie_parser import LottieParser

logging.basicConfig(level=logging.INFO)

parser = LottieParser()
link = "https://t.me/nft/SwagBag-98364"
print(f"Testing link: {link}")
parsed = parser.parse_link(link)
print(f"Parsed: {parsed}")

if parsed:
    name, gift_id = parsed
    url = parser.generate_lottie_url(name, gift_id)
    print(f"Generated URL: {url}")
    
    # Try to download (optional, might fail if network is restricted or URL is wrong)
    # result = parser.download_lottie_animation(name, gift_id, url)
    # print(f"Download result success: {result.get('success') if result else False}")
