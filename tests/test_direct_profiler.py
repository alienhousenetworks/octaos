import pytest
from app.services.sales_os.discovery.direct_profiler import DirectProfiler


def test_direct_profiler_html_parsing():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TechFlow Inc - Modern B2B Solutions</title>
        <!-- Meta Pixel Code -->
        <script>
            fbq('init', '1234567890');
            fbq('track', 'PageView');
        </script>
        <!-- Google tag (gtag.js) -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=AW-987654321"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('config', 'AW-987654321');
        </script>
    </head>
    <body class="home page-template-default wp-content">
        <h1>Welcome to TechFlow</h1>
        <p>Built with Next.js and Shopify</p>
        <div id="__NEXT_DATA__">{}</div>
        <script src="https://assets.website-files.com/site.js"></script>
        <footer>
            <p>Website built by <a href="https://pixelcraft.agency">PixelCraft Agency</a>.</p>
        </footer>
    </body>
    </html>
    """

    res = DirectProfiler.parse_html("techflow.io", "https://techflow.io", sample_html, 200)

    assert res.domain == "techflow.io"
    assert res.has_active_ad_spend is True
    assert "meta_pixel" in res.ad_pixels
    assert "google_ads" in res.ad_pixels

    # Tech stack
    assert "shopify" in res.tech_stack or "wordpress" in res.tech_stack or "nextjs" in res.tech_stack

    # Incumbent agency
    assert res.incumbent_agency is not None
    assert "PixelCraft" in res.incumbent_agency

    # Booking gap hypothesis
    assert res.has_online_booking is False
    assert any("instant calendar scheduling" in p for p in res.suggested_pain_points)
