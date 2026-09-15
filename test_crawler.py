from website_crawler import analyze_website

company = "Kunash Media Solution"

website = "https://kunashmedia.com/"

print("\nStarting website crawler...")
print("----------------------------------------")

result = analyze_website(
    company,
    website,
    max_pages=10
)

print("\n========================================")
print("CRAWLER RESULT")
print("========================================")

for key, value in result.items():

    print(f"{key}: {value}")

print("========================================")
