// Shopify Insights Fetcher Frontend JavaScript

class ShopifyInsightsFetcher {
    constructor() {
        this.initializeEventListeners();
        this.currentData = null;
        this.currentCurrencyMode = 'original'; // 'original' or 'usd'
        this.lastCurrencyInfo = null; // Store currency info for formatting
        this.setupPolicyModals();
    }

    initializeEventListeners() {
        // Form submission
        document.getElementById('urlForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.extractInsights();
        });

        // Example URL buttons
        document.querySelectorAll('.example-url').forEach(button => {
            button.addEventListener('click', (e) => {
                const url = e.target.getAttribute('data-url');
                document.getElementById('websiteUrl').value = url;
                this.extractInsights();
            });
        });

        // Download button
        document.getElementById('downloadBtn').addEventListener('click', () => {
            this.downloadJSON();
        });

        // Currency toggle button
        document.getElementById('currencyToggle').addEventListener('click', () => {
            this.toggleCurrency();
        });
    }

    async extractInsights() {
        const urlInput = document.getElementById('websiteUrl');
        const url = urlInput.value.trim();

        if (!url) {
            this.showError('Please enter a valid URL');
            return;
        }

        try {
            this.showLoading();
            
            const response = await fetch('/extract-insights', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    website_url: url
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to extract insights');
            }

            this.currentData = data;
            this.displayResults(data);

        } catch (error) {
            console.error('Error:', error);
            this.showError(error.message || 'An error occurred while extracting insights');
        }
    }

    showLoading() {
        document.getElementById('initialState').classList.add('d-none');
        document.getElementById('errorState').classList.add('d-none');
        document.getElementById('resultsContainer').classList.add('d-none');
        document.getElementById('loadingState').classList.remove('d-none');
    }

    showError(message) {
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('resultsContainer').classList.add('d-none');
        document.getElementById('initialState').classList.add('d-none');
        
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorState').classList.remove('d-none');
    }

    displayResults(data) {
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('errorState').classList.add('d-none');
        document.getElementById('initialState').classList.add('d-none');

        // Show currency toggle button if there are products with pricing
        const hasProducts = (data.hero_products && data.hero_products.length > 0) || 
                           (data.product_catalog && data.product_catalog.length > 0);
        if (hasProducts) {
            document.getElementById('currencyToggle').classList.remove('d-none');
        }

        // Populate sections
        this.populateBrandOverview(data);
        this.populateProducts(data);
        this.populateSocialContact(data);
        this.populatePoliciesFaqs(data);
        this.populateCompetitorAnalysis(data);
        this.populateAIValidation(data);
        this.populateRawJSON(data);

        document.getElementById('resultsContainer').classList.remove('d-none');
    }

    populateBrandOverview(data) {
        const container = document.getElementById('brandOverview');
        const brand = data.brand_context;
        
        let html = `
            <div class="row">
                <div class="col-md-8">
                    <h6><i class="fas fa-store me-2"></i>Brand Name</h6>
                    <p class="mb-3">${brand.brand_name || 'Not available'}</p>
                    
                    ${brand.brand_description ? `
                        <h6><i class="fas fa-info-circle me-2"></i>Description</h6>
                        <p class="mb-3">${brand.brand_description}</p>
                    ` : ''}
                    
                    ${brand.about_us_content ? `
                        <h6><i class="fas fa-book-open me-2"></i>About Us</h6>
                        <p class="mb-3">${this.truncateText(brand.about_us_content, 300)}</p>
                    ` : ''}
                </div>
                <div class="col-md-4">
                    <div class="stat-card">
                        <span class="stat-number">${data.total_products_found}</span>
                        <span class="stat-label">Total Products</span>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #6f42c1, #e83e8c);">
                        <span class="stat-number">${data.hero_products.length}</span>
                        <span class="stat-label">Hero Products</span>
                    </div>
                </div>
            </div>
        `;

        if (data.errors && data.errors.length > 0) {
            html += `
                <div class="alert alert-warning mt-3">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Extraction Notes</h6>
                    <ul class="mb-0">
                        ${data.errors.map(error => `<li>${error}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    populateProducts(data) {
        const container = document.getElementById('productsSection');
        
        let html = '';

        // Hero Products (Products from the home page)
        if (data.hero_products && data.hero_products.length > 0) {
            const heroProductsId = 'heroProducts_' + Date.now();
            const showMoreBtn = 'showMoreHero_' + Date.now();
            const additionalProductsId = 'additionalHero_' + Date.now();
            
            html += `
                <div class="mb-4">
                    <div class="d-flex align-items-center mb-3">
                        <h6 class="mb-0"><i class="fas fa-star text-warning me-2"></i>Hero Products</h6>
                        <span class="badge bg-warning text-dark ms-2">Featured on Homepage</span>
                        <span class="badge bg-primary ms-2">${data.hero_products.length} total</span>
                    </div>
                    <div class="row" id="${heroProductsId}">
                        ${data.hero_products.slice(0, 6).map(product => this.createProductCard(product)).join('')}
                    </div>
                    ${data.hero_products.length > 6 ? `
                        <div class="row d-none" id="${additionalProductsId}">
                            ${data.hero_products.slice(6).map(product => this.createProductCard(product)).join('')}
                        </div>
                        <div class="text-center mt-3">
                            <button class="btn btn-outline-warning btn-sm" id="${showMoreBtn}">
                                <i class="fas fa-chevron-down me-1"></i>Show ${data.hero_products.length - 6} More Hero Products
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
            
            // Add event listener for expandable hero products
            setTimeout(() => {
                const showMoreButton = document.getElementById(showMoreBtn);
                const additionalProducts = document.getElementById(additionalProductsId);
                
                if (showMoreButton && additionalProducts) {
                    let isExpanded = false;
                    showMoreButton.addEventListener('click', () => {
                        if (isExpanded) {
                            additionalProducts.classList.add('d-none');
                            showMoreButton.innerHTML = `<i class="fas fa-chevron-down me-1"></i>Show ${data.hero_products.length - 6} More Hero Products`;
                            isExpanded = false;
                        } else {
                            additionalProducts.classList.remove('d-none');
                            showMoreButton.innerHTML = `<i class="fas fa-chevron-up me-1"></i>Show Less Hero Products`;
                            isExpanded = true;
                        }
                    });
                }
            }, 100);
        }

        // Sample from product catalog
        if (data.product_catalog && data.product_catalog.length > 0) {
            const catalogProductsId = 'catalogProducts_' + Date.now();
            const showMoreCatalogBtn = 'showMoreCatalog_' + Date.now();
            const additionalCatalogId = 'additionalCatalog_' + Date.now();
            
            html += `
                <div class="section-divider"></div>
                <div class="d-flex align-items-center mb-3">
                    <h6 class="mb-0"><i class="fas fa-box me-2"></i>Product Catalog</h6>
                    <span class="badge bg-secondary ms-2">Sample from Full Catalog</span>
                    <span class="badge bg-info ms-2">${data.product_catalog.length} total</span>
                </div>
                <div class="row" id="${catalogProductsId}">
                    ${data.product_catalog.slice(0, 8).map(product => this.createProductCard(product)).join('')}
                </div>
                ${data.product_catalog.length > 8 ? `
                    <div class="row d-none" id="${additionalCatalogId}">
                        ${data.product_catalog.slice(8).map(product => this.createProductCard(product)).join('')}
                    </div>
                    <div class="text-center mt-3">
                        <button class="btn btn-outline-secondary btn-sm" id="${showMoreCatalogBtn}">
                            <i class="fas fa-chevron-down me-1"></i>Show ${data.product_catalog.length - 8} More Products
                        </button>
                    </div>
                ` : ''}
            `;
            
            // Add event listener for expandable catalog products
            setTimeout(() => {
                const showMoreButton = document.getElementById(showMoreCatalogBtn);
                const additionalProducts = document.getElementById(additionalCatalogId);
                
                if (showMoreButton && additionalProducts) {
                    let isExpanded = false;
                    showMoreButton.addEventListener('click', () => {
                        if (isExpanded) {
                            additionalProducts.classList.add('d-none');
                            showMoreButton.innerHTML = `<i class="fas fa-chevron-down me-1"></i>Show ${data.product_catalog.length - 8} More Products`;
                            isExpanded = false;
                        } else {
                            additionalProducts.classList.remove('d-none');
                            showMoreButton.innerHTML = `<i class="fas fa-chevron-up me-1"></i>Show Less Products`;
                            isExpanded = true;
                        }
                    });
                }
            }, 100);
        }

        // If no products found
        if (!html) {
            html = `
                <div class="text-center py-4">
                    <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                    <h6 class="text-muted">No Products Found</h6>
                    <p class="text-muted">Unable to extract product information from this store</p>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    createProductCard(product) {
        const image = product.images && product.images.length > 0 ? product.images[0] : null;
        let price = 'Price not available';
        
        if (product.price !== null && product.price !== undefined) {
            // Always prioritize formatted_price if available (contains proper currency)
            if (product.formatted_price) {
                price = product.formatted_price;
            } else if (this.currentCurrencyMode === 'original' && product.original_price && product.currency_symbol) {
                // Show original currency with formatting
                price = `${product.currency_symbol}${product.original_price}`;
            } else if (this.currentCurrencyMode === 'usd' && product.price_usd) {
                // Show USD converted price
                price = `$${product.price_usd.toFixed(2)} USD`;
            } else {
                // Final fallback - check if we have currency context
                const currencyInfo = this.lastCurrencyInfo;
                if (currencyInfo && currencyInfo.symbol && currencyInfo.symbol !== '$') {
                    price = `${currencyInfo.symbol}${product.price}`;
                } else {
                    price = `$${product.price}`;
                }
            }
        }
        
        return `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="product-card">
                    <div class="d-flex">
                        ${image ? `
                            <img src="${image}" alt="${product.title}" class="product-image me-3" 
                                 onerror="this.style.display='none'">
                        ` : `
                            <div class="product-image me-3 bg-light d-flex align-items-center justify-content-center">
                                <i class="fas fa-image text-muted"></i>
                            </div>
                        `}
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${this.truncateText(product.title, 50)}</h6>
                            <p class="text-success mb-1 fw-bold price-display">${price}</p>
                            ${product.vendor ? `<small class="text-muted">by ${product.vendor}</small>` : ''}
                            ${product.url ? `
                                <div class="mt-2">
                                    <a href="${product.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                        <i class="fas fa-external-link-alt me-1"></i>View
                                    </a>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupPolicyModals() {
        // Setup policy modal functionality
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('policy-link')) {
                e.preventDefault();
                const policyUrl = e.target.getAttribute('data-policy-url');
                const policyTitle = e.target.getAttribute('data-policy-title');
                this.showPolicyModal(policyUrl, policyTitle);
            }
        });
    }

    async showPolicyModal(policyUrl, policyTitle) {
        const modal = new bootstrap.Modal(document.getElementById('policyModal'));
        const modalBody = document.getElementById('policyModalBody');
        const modalTitle = document.getElementById('policyModalLabel');
        const viewOriginalBtn = document.getElementById('policyModalViewOriginal');

        // Set title and original link
        modalTitle.textContent = policyTitle;
        viewOriginalBtn.href = policyUrl;

        // Show loading state
        modalBody.innerHTML = `
            <div class="text-center">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading ${policyTitle.toLowerCase()} content...</p>
            </div>
        `;

        modal.show();

        try {
            // Use trafilatura to extract clean content
            const response = await fetch('/extract-policy-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    policy_url: policyUrl
                })
            });

            const data = await response.json();

            if (data.success && data.content) {
                modalBody.innerHTML = `
                    <div class="policy-content">
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Content extracted from: <strong>${policyTitle}</strong>
                        </div>
                        <div class="content-text" style="max-height: 400px; overflow-y: auto;">
                            ${this.formatPolicyContent(data.content)}
                        </div>
                    </div>
                `;
            } else {
                modalBody.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Could not extract content from this policy page. Please use the "View Original" button to access the full policy.
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading policy content:', error);
            modalBody.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Error loading policy content. Please use the "View Original" button to access the full policy.
                </div>
            `;
        }
    }

    formatPolicyContent(content) {
        // Format the content for better readability
        return content
            .replace(/\n\s*\n/g, '</p><p>')
            .replace(/^\s*/, '<p>')
            .replace(/\s*$/, '</p>')
            .replace(/(\d+\.\s)/g, '<br><strong>$1</strong>')
            .replace(/(PRIVACY POLICY|TERMS OF SERVICE|RETURN POLICY|REFUND POLICY)/gi, '<h6>$1</h6>');
    }

    populateSocialContact(data) {
        const container = document.getElementById('socialContactSection');
        const social = data.social_handles;
        const contact = data.contact_details;
        
        let html = '<div class="row">';

        // Social Media
        html += '<div class="col-md-6">';
        html += '<h6><i class="fas fa-share-alt me-2"></i>Social Media</h6>';
        
        const socialPlatforms = [
            { key: 'instagram', icon: 'fab fa-instagram', color: '#E4405F' },
            { key: 'facebook', icon: 'fab fa-facebook', color: '#1877F2' },
            { key: 'twitter', icon: 'fab fa-twitter', color: '#1DA1F2' },
            { key: 'tiktok', icon: 'fab fa-tiktok', color: '#000000' },
            { key: 'youtube', icon: 'fab fa-youtube', color: '#FF0000' },
            { key: 'linkedin', icon: 'fab fa-linkedin', color: '#0A66C2' },
            { key: 'pinterest', icon: 'fab fa-pinterest', color: '#BD081C' }
        ];

        const foundSocial = socialPlatforms.filter(platform => social[platform.key]);
        
        if (foundSocial.length > 0) {
            foundSocial.forEach(platform => {
                html += `
                    <a href="#" class="social-handle" style="border-left: 4px solid ${platform.color}">
                        <i class="${platform.icon}"></i>
                        ${social[platform.key]}
                    </a>
                `;
            });
        } else {
            html += '<p class="text-muted">No social media handles found</p>';
        }
        
        html += '</div>';

        // Contact Information
        html += '<div class="col-md-6">';
        html += '<h6><i class="fas fa-address-book me-2"></i>Contact Information</h6>';
        
        if (contact.emails && contact.emails.length > 0) {
            html += '<div class="mb-3">';
            html += '<strong><i class="fas fa-envelope me-2"></i>Email:</strong><br>';
            contact.emails.forEach(email => {
                html += `<div class="contact-item"><a href="mailto:${email}">${email}</a></div>`;
            });
            html += '</div>';
        }

        if (contact.phone_numbers && contact.phone_numbers.length > 0) {
            html += '<div class="mb-3">';
            html += '<strong><i class="fas fa-phone me-2"></i>Phone:</strong><br>';
            contact.phone_numbers.forEach(phone => {
                html += `<div class="contact-item"><a href="tel:${phone}">${phone}</a></div>`;
            });
            html += '</div>';
        }

        if (contact.address) {
            html += `
                <div class="mb-3">
                    <strong><i class="fas fa-map-marker-alt me-2"></i>Address:</strong><br>
                    <div class="contact-item">${contact.address}</div>
                </div>
            `;
        }

        if (!contact.emails?.length && !contact.phone_numbers?.length && !contact.address) {
            html += '<p class="text-muted">No contact information found</p>';
        }

        html += '</div></div>';

        // Important Links
        const links = data.important_links;
        const linkItems = [
            { key: 'order_tracking', label: 'Order Tracking', icon: 'fas fa-truck' },
            { key: 'contact_us', label: 'Contact Us', icon: 'fas fa-envelope' },
            { key: 'blogs', label: 'Blog', icon: 'fas fa-blog' },
            { key: 'size_guide', label: 'Size Guide', icon: 'fas fa-ruler' },
            { key: 'shipping_info', label: 'Shipping Info', icon: 'fas fa-shipping-fast' },
            { key: 'about_us', label: 'About Us', icon: 'fas fa-info-circle' },
            { key: 'careers', label: 'Careers', icon: 'fas fa-briefcase' }
        ];

        const foundLinks = linkItems.filter(item => links[item.key]);
        
        if (foundLinks.length > 0) {
            html += '<div class="section-divider"></div>';
            html += '<h6><i class="fas fa-link me-2"></i>Important Links</h6>';
            html += '<div class="row">';
            
            foundLinks.forEach(item => {
                html += `
                    <div class="col-md-6 mb-2">
                        <div class="link-item">
                            <i class="${item.icon} me-2"></i>
                            <a href="${links[item.key]}" target="_blank">${item.label}</a>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        }

        container.innerHTML = html;
    }

    populatePoliciesFaqs(data) {
        const container = document.getElementById('policiesFaqsSection');
        const policies = data.policies;
        const faqs = data.faqs;
        
        let html = '<div class="row">';

        // Policies
        html += '<div class="col-md-6">';
        html += '<h6><i class="fas fa-file-contract me-2"></i>Policies</h6>';
        
        const policyItems = [
            { key: 'privacy_policy_url', label: 'Privacy Policy' },
            { key: 'return_policy_url', label: 'Return Policy' },
            { key: 'refund_policy_url', label: 'Refund Policy' },
            { key: 'terms_of_service_url', label: 'Terms of Service' }
        ];

        const foundPolicies = policyItems.filter(item => policies[item.key]);
        
        if (foundPolicies.length > 0) {
            foundPolicies.forEach(item => {
                html += `
                    <div class="mb-2">
                        <i class="fas fa-file-alt me-2"></i>
                        <a href="#" class="policy-link" data-policy-url="${policies[item.key]}" data-policy-title="${item.label}">${item.label}</a>
                    </div>
                `;
            });
        } else {
            html += '<p class="text-muted">No policy links found</p>';
        }
        
        html += '</div>';

        // FAQs
        html += '<div class="col-md-6">';
        html += '<h6><i class="fas fa-question-circle me-2"></i>FAQs</h6>';
        
        if (faqs && faqs.length > 0) {
            html += '<div style="max-height: 400px; overflow-y: auto;">';
            faqs.slice(0, 5).forEach((faq, index) => {
                html += `
                    <div class="faq-item">
                        <div class="faq-question">${faq.question}</div>
                        <div class="faq-answer">${this.truncateText(faq.answer, 150)}</div>
                    </div>
                `;
            });
            html += '</div>';
            
            if (faqs.length > 5) {
                html += `<small class="text-muted">+${faqs.length - 5} more FAQs available in full dataset</small>`;
            }
        } else {
            html += '<p class="text-muted">No FAQs found</p>';
        }
        
        html += '</div></div>';

        container.innerHTML = html;
    }

    populateAIValidation(data) {
        if (!data.ai_validation || !data.ai_validation.validated) {
            return; // Skip if no AI validation data
        }

        const container = document.getElementById('policiesFaqsSection');
        const validation = data.ai_validation;
        
        // Add AI validation section at the end
        const aiValidationHtml = `
            <div class="section-divider"></div>
            <h6><i class="fas fa-robot me-2"></i>AI Quality Assessment</h6>
            <div class="row">
                <div class="col-md-6">
                    <div class="stat-card" style="background: linear-gradient(135deg, #17a2b8, #007bff);">
                        <span class="stat-number">${Math.round(validation.confidence_score * 100)}%</span>
                        <span class="stat-label">Data Quality Score</span>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="alert ${validation.confidence_score >= 0.8 ? 'alert-success' : validation.confidence_score >= 0.6 ? 'alert-warning' : 'alert-danger'}">
                        <strong>Assessment:</strong> 
                        ${validation.confidence_score >= 0.8 ? 'Excellent data quality' : 
                          validation.confidence_score >= 0.6 ? 'Good with room for improvement' : 
                          'Needs significant improvement'}
                    </div>
                </div>
            </div>
            
            ${validation.validation_notes && validation.validation_notes.length > 0 ? `
                <div class="mt-3">
                    <h6><i class="fas fa-lightbulb me-2"></i>AI Insights & Recommendations</h6>
                    <div style="max-height: 200px; overflow-y: auto;">
                        ${validation.validation_notes.map(note => `
                            <div class="alert alert-info py-2 mb-2">
                                <small><i class="fas fa-info-circle me-1"></i>${note}</small>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
        
        container.innerHTML += aiValidationHtml;
    }

    populateCompetitorAnalysis(data) {
        if (!data.competitor_analysis || data.competitor_analysis.competitors_found === 0) {
            return; // Skip if no competitor data
        }

        const container = document.getElementById('socialContactSection');
        const analysis = data.competitor_analysis;
        
        // Add competitor analysis section
        const competitorHtml = `
            <div class="section-divider"></div>
            <h6><i class="fas fa-chart-line me-2"></i>Competitive Analysis</h6>
            <div class="row">
                <div class="col-md-6">
                    <div class="stat-card" style="background: linear-gradient(135deg, #28a745, #20c997);">
                        <span class="stat-number">${analysis.competitors_found}</span>
                        <span class="stat-label">Competitors Found</span>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="alert alert-info">
                        <strong>Market Position:</strong> ${analysis.market_positioning}
                    </div>
                </div>
            </div>
            
            ${analysis.competitor_insights && analysis.competitor_insights.length > 0 ? `
                <div class="mt-3">
                    <h6><i class="fas fa-users me-2"></i>Key Competitors</h6>
                    <div class="row">
                        ${analysis.competitor_insights.map(competitor => `
                            <div class="col-md-6 mb-3">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">${competitor.brand_name}</h6>
                                        <p class="card-text">
                                            <small class="text-muted">${competitor.store_url}</small><br>
                                            <strong>Products:</strong> ${competitor.product_count}<br>
                                            <strong>Price Range:</strong> ${competitor.price_range}<br>
                                            <strong>Social Score:</strong> ${competitor.social_presence_score}/100
                                        </p>
                                        ${competitor.strengths && competitor.strengths.length > 0 ? `
                                            <div class="mb-2">
                                                <strong>Strengths:</strong>
                                                <ul class="list-unstyled">
                                                    ${competitor.strengths.map(strength => `<li><i class="fas fa-plus-circle text-success me-1"></i>${strength}</li>`).join('')}
                                                </ul>
                                            </div>
                                        ` : ''}
                                        ${competitor.weaknesses && competitor.weaknesses.length > 0 ? `
                                            <div>
                                                <strong>Opportunities:</strong>
                                                <ul class="list-unstyled">
                                                    ${competitor.weaknesses.map(weakness => `<li><i class="fas fa-exclamation-triangle text-warning me-1"></i>${weakness}</li>`).join('')}
                                                </ul>
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${analysis.competitive_analysis ? `
                <div class="mt-3">
                    <h6><i class="fas fa-lightbulb me-2"></i>Competitive Insights</h6>
                    <div class="alert alert-secondary">
                        <pre style="white-space: pre-wrap; margin: 0;">${analysis.competitive_analysis}</pre>
                    </div>
                </div>
            ` : ''}
        `;
        
        container.innerHTML += competitorHtml;
    }

    populateRawJSON(data) {
        const container = document.getElementById('rawJson');
        container.textContent = JSON.stringify(data, null, 2);
    }

    toggleCurrency() {
        if (!this.currentData) return;
        
        this.currentCurrencyMode = this.currentCurrencyMode === 'original' ? 'usd' : 'original';
        
        // Update toggle button text
        const toggleBtn = document.getElementById('currencyToggle');
        if (this.currentCurrencyMode === 'original') {
            toggleBtn.innerHTML = '<i class="fas fa-dollar-sign me-1"></i>Switch to USD';
            toggleBtn.className = 'btn btn-outline-secondary btn-sm';
        } else {
            toggleBtn.innerHTML = '<i class="fas fa-globe me-1"></i>Switch to Original';
            toggleBtn.className = 'btn btn-outline-primary btn-sm';
        }
        
        // Re-render products with new currency
        this.populateProducts(this.currentData);
    }

    downloadJSON() {
        if (!this.currentData) return;
        
        const dataStr = JSON.stringify(this.currentData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `shopify-insights-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ShopifyInsightsFetcher();
});
