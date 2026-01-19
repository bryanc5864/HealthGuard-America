# HealthGuard Visual Enhancement Opportunities

This document outlines all locations where images, banners, icons, and visual elements can be added to improve the website's appearance and user experience.

---

## 1. Landing Page (`/`)
**File:** `frontend/templates/landing.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Hero Background | Background Image/Video | Healthcare-themed hero image (doctors, hospitals, families) or subtle animated gradient |
| Logo | Image | HealthGuard America logo (SVG preferred) - replace the Bootstrap icon |
| Public Portal Card | Illustration | Family/people illustration representing public access |
| Government Portal Card | Illustration | Official building or government seal illustration |
| Footer | Logo/Badges | Data source logos (CMS, FDA, HRSA, CDC) |

### Specific Insertions:
```html
<!-- Before hero-title -->
<img src="/static/images/logo.svg" alt="HealthGuard" class="hero-logo" style="height: 80px;">

<!-- Hero background -->
<style>
.hero {
    background-image: url('/static/images/hero-bg.jpg');
    background-size: cover;
}
</style>
```

---

## 2. Public Portal Home (`/public/`)
**File:** `frontend/templates/public/home.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Page Header | Banner | Welcome banner with healthcare imagery |
| PriceVision Card | Icon/Illustration | Hospital/money illustration |
| DrugWatch Card | Icon/Illustration | Pill/pharmacy illustration |
| FoodScore Card | Icon/Illustration | Grocery/healthy food illustration |
| Stats Section | Background | Subtle pattern or gradient background |
| Stats Icons | Custom Icons | Animated count-up icons |

### Specific Insertions:
```html
<!-- Hero banner at top -->
<div class="hero-banner" style="background: url('/static/images/public-banner.jpg');">
    <h1>Public Portal</h1>
</div>

<!-- Module card images -->
<img src="/static/images/modules/pricevision-icon.svg" class="module-illustration">
```

---

## 3. Government Portal Home (`/gov/`)
**File:** `frontend/templates/gov/home.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Header Area | Official Seal | Government or HHS seal image |
| Module Cards | Module Icons | Custom SVG icons for each module |
| Stats Section | Infographic | Data visualization summary |
| Sidebar (if added) | Agency Logos | HHS, CMS, FDA logos |

---

## 4. PriceVision Module

### Home Page (`/public/pricevision/`, `/gov/pricevision/`)
**Files:** `frontend/templates/*/pricevision/home.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Hero Section | Banner | Hospital/medical facility image |
| Search Box | Background Icon | Magnifying glass or hospital icon |
| Stats Cards | Icons | Custom icons for hospitals, procedures, states |
| "How It Works" Section | Illustrations | Step-by-step process illustrations |

### Hospital Detail Page (`/pricevision/hospital/<npi>`)
**Files:** `frontend/templates/*/pricevision/hospital.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Hospital Header | Hospital Photo | Hospital exterior image (via API or placeholder) |
| Hospital Info Card | Map | Embedded map showing hospital location |
| Rating Display | Star Icons | Visual star rating display |
| Price Table | Price Icons | Dollar sign icons for price columns |

### Compare Page (`/pricevision/compare`)
**Files:** `frontend/templates/*/pricevision/compare.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Header | Comparison Graphic | Side-by-side comparison illustration |
| Price Cards | Hospital Thumbnails | Hospital images or placeholder icons |
| Savings Section | Money Illustration | Piggy bank or savings illustration |
| Best Value Badge | Custom Badge | Eye-catching "Best Value" badge image |

---

## 5. DrugWatch Module

### Home Page (`/public/drugwatch/`, `/gov/drugwatch/`)
**Files:** `frontend/templates/*/drugwatch/home.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Hero Section | Banner | Pharmacy/medication imagery |
| Top Expensive Drugs | Drug Icons | Pill/capsule illustrations |
| Country Comparison | Flag Icons | US, Canada, Australia, UK flags |
| Stats Section | Infographic | Drug pricing infographic |

### Drug Detail Page (`/drugwatch/drug/<drug_id>`)
**Files:** `frontend/templates/*/drugwatch/drug.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Drug Header | Drug Image | Medication image or generic pill icon |
| Manufacturer Info | Company Logo | Pharmaceutical company logos |
| Price Chart | Chart Background | Subtle gradient background |
| Country Comparison | Flags | Country flag icons next to prices |

### MFN Analysis Page (`/gov/drugwatch/mfn`)
**File:** `frontend/templates/gov/drugwatch/mfn.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Header | Policy Graphic | Government policy illustration |
| Savings Calculator | Calculator Icon | Interactive calculator graphic |
| World Map | Map Visualization | World map showing price comparisons |

### Trends Page (`/gov/drugwatch/trends`)
**File:** `frontend/templates/gov/drugwatch/trends.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Header | Trend Graphic | Upward/downward trend illustration |
| Charts Section | Chart Backgrounds | Subtle grid or pattern backgrounds |

---

## 6. FoodScore Module

### Home Page (`/public/foodscore/`, `/gov/foodscore/`)
**Files:** `frontend/templates/*/foodscore/home.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Hero Section | Banner | Fresh food/grocery imagery |
| Category Icons | Food Icons | Icons for each food category |
| NOVA Distribution | Colored Icons | Processing level illustrations |
| High Risk Products | Warning Graphics | Attention-grabbing warning icons |

### Product Detail Page (`/foodscore/product/<barcode>`)
**Files:** `frontend/templates/*/foodscore/product.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Product Header | Product Image | Actual product image (via OpenFoodFacts API) |
| Nutri-Score | Grade Badge | A/B/C/D/E letter grade badges (official Nutri-Score images) |
| NOVA Group | NOVA Icons | Official NOVA classification icons |
| Additive List | Risk Icons | Color-coded risk level icons |
| Ingredients | Ingredient Icons | Icons for common allergens |

### Scan Page (`/public/foodscore/scan`)
**File:** `frontend/templates/public/foodscore/scan.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Scanner Area | Scanner Frame | Barcode scanner overlay graphic |
| Instructions | Step Illustrations | How-to-scan illustrations |
| Camera Permission | Camera Icon | Camera permission request graphic |

### SNAP Analysis Page (`/gov/foodscore/snap`)
**File:** `frontend/templates/gov/foodscore/snap.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Header | SNAP Logo | Official SNAP/EBT logo |
| Eligibility Section | Checkmark Graphics | Eligible/ineligible icons |
| Nutrition Info | Food Pyramid | Nutritional guidance illustration |

---

## 7. RuralAccess Module (Government Only)

### Home Page (`/gov/ruralaccess/`)
**File:** `frontend/templates/gov/ruralaccess/home.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Hero Section | Map Preview | US map preview image |
| Stats Cards | Location Icons | Rural/urban location icons |
| Shortage Levels | Color-coded Icons | Critical/High/Moderate/Low icons |

### Interactive Map (`/gov/ruralaccess/map`)
**File:** `frontend/templates/gov/ruralaccess/map.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Map Markers | Custom Markers | Hospital/clinic custom map markers |
| Legend | Legend Icons | Shortage level indicator icons |
| Sidebar | Area Images | Regional healthcare facility images |

### County Detail (`/gov/ruralaccess/county/<fips>`)
**File:** `frontend/templates/gov/ruralaccess/county.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| County Header | County Map | County boundary map image |
| Demographics | Population Icons | People/demographic icons |
| Facilities List | Facility Icons | Hospital/clinic type icons |

### Analytics Page (`/gov/ruralaccess/analytics`)
**File:** `frontend/templates/gov/ruralaccess/analytics.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Chart Headers | Section Icons | Analysis icons for each chart |
| Map Visualization | Choropleth Background | US states outline |

---

## 8. ChronicCare Module (Government Only)

### Home Page (`/gov/chroniccare/`)
**File:** `frontend/templates/gov/chroniccare/home.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Hero Section | Health Graphic | Chronic disease awareness imagery |
| Disease Cards | Disease Icons | Heart, diabetes, obesity icons |
| Risk Map Preview | US Map | Choropleth map preview |

### Dashboard (`/gov/chroniccare/dashboard`)
**File:** `frontend/templates/gov/chroniccare/dashboard.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| KPI Cards | Health Icons | Heart rate, BMI, glucose icons |
| Charts | Chart Backgrounds | Medical-themed subtle backgrounds |
| Risk Indicators | Gauge Graphics | Risk level gauge illustrations |

### County Detail (`/gov/chroniccare/county/<fips>`)
**File:** `frontend/templates/gov/chroniccare/county.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| County Header | County Image | County representative image |
| Health Metrics | Progress Icons | Health metric progress indicators |
| Comparison Section | Benchmark Graphics | National vs local comparison |

### Correlations Page (`/gov/chroniccare/correlations`)
**File:** `frontend/templates/gov/chroniccare/correlations.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Correlation Matrix | Heat Map | Color-coded correlation visualization |
| Factor Icons | Variable Icons | Icons for each health factor |

### Interventions Page (`/gov/chroniccare/interventions`)
**File:** `frontend/templates/gov/chroniccare/interventions.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Priority Counties | Alert Icons | Priority level indicators |
| Intervention Cards | Action Icons | Intervention type icons |
| Success Stories | Before/After | Intervention success graphics |

---

## 9. Global Elements

### Navigation Bar
**Files:** `frontend/templates/*/base_*.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Logo | SVG Logo | HealthGuard logo in navbar |
| Module Icons | Nav Icons | Small icons next to each nav item |
| User Avatar | Profile Icon | User profile picture/avatar |

### Footer
**Files:** `frontend/templates/*/base_*.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Logo | Footer Logo | HealthGuard logo (light version for dark footer) |
| Partner Logos | Agency Logos | CMS, FDA, HRSA, CDC, HHS logos |
| Social Icons | Social Media | Twitter, GitHub, LinkedIn icons |
| Certification Badges | Trust Badges | Security/compliance badges |

### Login Page (`/gov/login`)
**File:** `frontend/templates/gov/login.html`

| Location | Type | Suggested Content |
|----------|------|-------------------|
| Background | Full-page Background | Government/healthcare themed background |
| Logo | Large Logo | Centered HealthGuard logo |
| Form Card | Card Background | Subtle gradient or pattern |
| Security Badge | Trust Badge | "Secure Login" badge |

---

## 10. Recommended Image Assets to Create

### High Priority
1. `logo.svg` - Main HealthGuard logo
2. `logo-white.svg` - White version for dark backgrounds
3. `hero-bg.jpg` - Landing page hero background (1920x1080)
4. `public-banner.jpg` - Public portal banner (1920x400)
5. `gov-banner.jpg` - Government portal banner (1920x400)

### Module Icons (SVG)
6. `pricevision-icon.svg`
7. `drugwatch-icon.svg`
8. `foodscore-icon.svg`
9. `ruralaccess-icon.svg`
10. `chroniccare-icon.svg`

### Illustrations
11. `hospital-illustration.svg` - For PriceVision
12. `pharmacy-illustration.svg` - For DrugWatch
13. `grocery-illustration.svg` - For FoodScore
14. `map-illustration.svg` - For RuralAccess
15. `health-illustration.svg` - For ChronicCare

### Badges & Icons
16. `nutriscore-a.svg` through `nutriscore-e.svg`
17. `nova-1.svg` through `nova-4.svg`
18. `us-flag.svg`, `canada-flag.svg`, `uk-flag.svg`, `australia-flag.svg`
19. `best-value-badge.svg`
20. `verified-badge.svg`

### Backgrounds
21. `pattern-dots.svg` - Subtle dot pattern
22. `pattern-grid.svg` - Grid pattern for charts
23. `gradient-blue.svg` - Government portal gradient
24. `gradient-green.svg` - Public portal gradient

---

## 11. CSS Enhancements Needed

```css
/* Hero sections with background images */
.hero-banner {
    background-size: cover;
    background-position: center;
    position: relative;
}

.hero-banner::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
}

/* Module card hover effects */
.module-card:hover .module-illustration {
    transform: scale(1.1);
    transition: transform 0.3s ease;
}

/* Animated stats */
.stat-value {
    animation: countUp 1s ease-out;
}

/* Badge animations */
.best-value-badge {
    animation: pulse 2s infinite;
}
```

---

## 12. Suggested Image Sources

- **Unsplash** - Free high-quality photos (healthcare, hospitals)
- **Pexels** - Free stock photos
- **unDraw** - Free SVG illustrations
- **Flaticon** - Icons (with attribution)
- **Heroicons** - Free SVG icons
- **Font Awesome** - Icon library (already using Bootstrap Icons)
- **Lottie** - Animated illustrations
- **OpenFoodFacts** - Product images via API

---

## 13. File Structure for Images

```
frontend/static/
├── images/
│   ├── logo/
│   │   ├── logo.svg
│   │   ├── logo-white.svg
│   │   └── favicon.ico
│   ├── heroes/
│   │   ├── landing-hero.jpg
│   │   ├── public-banner.jpg
│   │   └── gov-banner.jpg
│   ├── modules/
│   │   ├── pricevision/
│   │   │   ├── icon.svg
│   │   │   └── illustration.svg
│   │   ├── drugwatch/
│   │   ├── foodscore/
│   │   ├── ruralaccess/
│   │   └── chroniccare/
│   ├── badges/
│   │   ├── nutriscore/
│   │   ├── nova/
│   │   └── trust/
│   ├── flags/
│   │   ├── us.svg
│   │   ├── canada.svg
│   │   ├── uk.svg
│   │   └── australia.svg
│   ├── partners/
│   │   ├── cms.svg
│   │   ├── fda.svg
│   │   ├── hrsa.svg
│   │   └── cdc.svg
│   └── backgrounds/
│       ├── pattern-dots.svg
│       └── pattern-grid.svg
```

---

## Summary

**Total image insertion points identified: 100+**

### By Priority:
- **Critical (Landing & Home pages):** 15 locations
- **High (Module home pages):** 25 locations
- **Medium (Detail pages):** 40 locations
- **Low (Analytics/Admin pages):** 20+ locations

### By Type:
- Logos: 5
- Hero banners: 8
- Module illustrations: 15
- Icons: 50+
- Badges: 10
- Background patterns: 5
- Partner/Trust logos: 10
