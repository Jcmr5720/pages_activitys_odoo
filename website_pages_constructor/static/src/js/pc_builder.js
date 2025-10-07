odoo.define('website_pages_constructor.pc_builder', function (require) {
    'use strict';

    var ajax = require('web.ajax');

    $(document).ready(function () {
        var $page = $('#pc-builder-page');
        var $pageLoader = $('#pc-builder-loading');
        var loaderHidden = false;

        function hidePageLoader() {
            if (loaderHidden) {
                return;
            }
            loaderHidden = true;
            $('body').removeClass('pc-builder-lock-scroll');
            $(window).off('load.pc_builder', hidePageLoader);
            if ($pageLoader.length) {
                $pageLoader.addClass('pc-builder-loading-hidden');
                setTimeout(function () {
                    $pageLoader.remove();
                }, 400);
            }
        }

        if (!$page.length) {
            hidePageLoader();
            return;
        }

        if ($pageLoader.length) {
            $('body').addClass('pc-builder-lock-scroll');
            $(window).on('load.pc_builder', hidePageLoader);
        }
        var selections = {};
        var storageKey = 'pc_builder_selections';
        var stored = localStorage.getItem(storageKey);
        if (stored) {
            try {
                selections = JSON.parse(stored);
            } catch (e) {
                selections = {};
            }
        }
        var isPublic = $page.data('is-public') === 1 || $page.data('is-public') === '1';
        function buildSpinnerMarkup(options) {
            options = options || {};
            var message = options.message || 'Cargando componentes...';
            var extraClass = options.variant === 'inline' ? ' pc-builder-spinner-inline' : '';
            return (
                '<div class="pc-builder-spinner' +
                extraClass +
                '" role="status" aria-live="polite">' +
                '<div class="pc-builder-monitor">' +
                '<div class="pc-builder-monitor-header">' +
                '<span class="pc-builder-dot dot-red"></span>' +
                '<span class="pc-builder-dot dot-yellow"></span>' +
                '<span class="pc-builder-dot dot-green"></span>' +
                '</div>' +
                '<div class="pc-builder-monitor-body">' +
                '<span class="pc-builder-code-line line1"></span>' +
                '<span class="pc-builder-code-line line2"></span>' +
                '<span class="pc-builder-code-line line3"></span>' +
                '<span class="pc-builder-code-line line4"></span>' +
                '</div>' +
                '</div>' +
                '<div class="pc-builder-monitor-stand"></div>' +
                '<div class="pc-builder-keyboard">' +
                '<span class="pc-builder-key key-left"></span>' +
                '<span class="pc-builder-key key-middle"></span>' +
                '<span class="pc-builder-key key-right"></span>' +
                '</div>' +
                '<p class="pc-builder-loading-text">' +
                message +
                '</p>' +
                '</div>'
            );
        }
        function showOutOfStockProducts() {
            return $('#toggle-out-of-stock').is(':checked');
        }

        function showOnlyCompatibleProducts() {
            var $checkbox = $('#toggle-compatible-only');
            if (!$checkbox.length) {
                return false;
            }
            return $checkbox.is(':checked');
        }

        function parseStockValue(value) {
            if (value === undefined || value === null || value === '') {
                return null;
            }
            if (typeof value === 'number') {
                return isNaN(value) ? null : value;
            }
            var parsed = parseFloat(value);
            return isNaN(parsed) ? null : parsed;
        }

        function parsePriceValue(value) {
            if (typeof value === 'number') {
                return isNaN(value) ? 0 : value;
            }
            var parsed = parseFloat(value);
            return isNaN(parsed) ? 0 : parsed;
        }

        var currencyFormatter = new Intl.NumberFormat('es-CO', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });

        function formatPriceDisplay(value) {
            var numericValue = typeof value === 'number' ? value : parsePriceValue(value);
            if (!isFinite(numericValue)) {
                numericValue = 0;
            }
            return '$' + currencyFormatter.format(numericValue);
        }

        var DEFAULT_MAX_PRODUCTS = 10;
        var $maxProductsInput = $('#max-products-per-category');
        if ($maxProductsInput.length) {
            var initialMax = parseInt($maxProductsInput.val(), 10);
            if (isNaN(initialMax) || initialMax <= 0) {
                $maxProductsInput.val(DEFAULT_MAX_PRODUCTS);
            }
        }

        var $optionsPanel = $('#builder-options-panel');
        var $optionsPanelBody = $('#options-panel-body');
        var $optionsToggle = $('#options-panel-toggle');
        var $optionsToggleLabel = $optionsToggle.find('.visually-hidden');

        if ($optionsToggle.length && $optionsPanelBody.length) {
            $optionsToggle.on('click', function () {
                var isOpen = $optionsPanelBody.is(':visible');
                if (isOpen) {
                    $optionsPanelBody.slideUp(150, function () {
                        $optionsToggle.attr('aria-expanded', 'false');
                        $optionsToggle.find('i').removeClass('fa-minus').addClass('fa-plus');
                        $optionsPanel.addClass('collapsed');
                        if ($optionsToggleLabel.length) {
                            $optionsToggleLabel.text('Expandir opciones');
                        }
                    });
                } else {
                    $optionsPanelBody.slideDown(150, function () {
                        $optionsToggle.attr('aria-expanded', 'true');
                        $optionsToggle.find('i').removeClass('fa-plus').addClass('fa-minus');
                        $optionsPanel.removeClass('collapsed');
                        if ($optionsToggleLabel.length) {
                            $optionsToggleLabel.text('Contraer opciones');
                        }
                    });
                }
            });
        }

        function getMaxProductsPerCategory() {
            var $input = $('#max-products-per-category');
            if (!$input.length) {
                return DEFAULT_MAX_PRODUCTS;
            }
            var value = parseInt($input.val(), 10);
            if (isNaN(value) || value <= 0) {
                return DEFAULT_MAX_PRODUCTS;
            }
            return value;
        }

        function getStoredSearchTerm($container) {
            var term = $container.data('searchTerm');
            return typeof term === 'string' ? term : '';
        }

        function isOutOfStockProduct(product) {
            if (!product) {
                return false;
            }
            var stockValue = parseStockValue(product.stock);
            if (stockValue === null) {
                return false;
            }
            return stockValue <= 0;
        }

        function shouldConsiderSelection(catId) {
            var product = selections[catId];
            if (!product) {
                return false;
            }
            if (showOutOfStockProducts()) {
                return true;
            }
            var stockValue = parseStockValue(product.stock);
            if (stockValue === null) {
                return true;
            }
            return stockValue > 0;
        }

        function getActiveSelectionEntries() {
            var entries = [];
            $.each(selections, function (catId, product) {
                if (shouldConsiderSelection(catId)) {
                    entries.push({ catId: catId, product: product });
                }
            });
            return entries;
        }

        function getComparableSelectedIds(excludeCatId) {
            var ids = [];
            $.each(selections, function (catId, product) {
                if (parseInt(catId, 10) === parseInt(excludeCatId, 10)) {
                    return;
                }
                if (shouldConsiderSelection(catId)) {
                    ids.push(product.id);
                }
            });
            return ids;
        }

        function getActiveProducts() {
            return getActiveSelectionEntries().map(function (entry) {
                return entry.product;
            });
        }

        function saveSelections() {
            localStorage.setItem(storageKey, JSON.stringify(selections));
        }

        function showLoadingSpinner($container) {
            var markup = buildSpinnerMarkup({
                variant: 'inline',
                message: 'Cargando hardware compatible...',
            });
            $container
                .empty()
                .append('<div class="col-12 loading-placeholder">' + markup + '</div>');
        }

        function hideLoadingSpinner($container) {
            $container.find('.loading-placeholder').remove();
        }
        function showAlert(msg) {
            $('#compat-alert').text(msg).removeClass('d-none');
        }
        function hideAlert() {
            $('#compat-alert').addClass('d-none').text('');
        }
        var initialCategory = $('#pc-builder-menu .category[data-initial="1"]').data('category-id');
        var initialMenu = $('#pc-builder-main-menu .main-menu-item[data-initial="1"]').data('group');

        function showInitialGroup() {
            if (initialCategory) {
                var initGroup = $('#pc-builder-menu .category[data-category-id="' + initialCategory + '"]').data('group');
                $('#pc-builder-main-menu .main-menu-item').removeClass('active');
                $('#pc-builder-main-menu .main-menu-item[data-group="' + initGroup + '"]').addClass('active');
                $('#pc-builder-menu .category').each(function () {
                    $(this).toggle($(this).data('group') === initGroup);
                });
            } else if (initialMenu) {
                $('#pc-builder-main-menu .main-menu-item').removeClass('active');
                $('#pc-builder-main-menu .main-menu-item[data-group="' + initialMenu + '"]').addClass('active');
                $('#pc-builder-menu .category').each(function () {
                    $(this).toggle($(this).data('group') === initialMenu);
                });
            }
        }

        function isInitialRequirementSatisfied() {
            if (initialCategory) {
                return shouldConsiderSelection(initialCategory);
            }
            if (initialMenu) {
                var satisfied = false;
                $('#pc-builder-menu .category[data-group="' + initialMenu + '"]').each(function () {
                    var cid = $(this).data('category-id');
                    if (shouldConsiderSelection(cid)) {
                        satisfied = true;
                        return false;
                    }
                });
                return satisfied;
            }
            return true;
        }

        function updateLockState() {
            if (isInitialRequirementSatisfied()) {
                $('#pc-builder-main-menu .main-menu-item')
                    .removeClass('disabled')
                    .css('pointer-events', '')
                    .css('opacity', '');
                $('#pc-builder-menu .category button').prop('disabled', false);
                return;
            }
            if (initialCategory) {
                var initGroup = $('#pc-builder-menu .category[data-category-id="' + initialCategory + '"]').data('group');
                $('#pc-builder-main-menu .main-menu-item').each(function () {
                    var $item = $(this);
                    var group = $item.data('group');
                    if (group !== initGroup) {
                        $item.addClass('disabled').css('pointer-events', 'none').css('opacity', '0.5');
                    } else {
                        $item.removeClass('disabled').css('pointer-events', '').css('opacity', '');
                    }
                });
                $('#pc-builder-menu .category').each(function () {
                    var $cat = $(this);
                    var cid = $cat.data('category-id');
                    if (cid !== initialCategory) {
                        $cat.find('button').prop('disabled', true);
                    } else {
                        $cat.find('button').prop('disabled', false);
                    }
                });
            } else if (initialMenu) {
                $('#pc-builder-main-menu .main-menu-item').each(function () {
                    var $item = $(this);
                    var group = $item.data('group');
                    if (group !== initialMenu) {
                        $item.addClass('disabled').css('pointer-events', 'none').css('opacity', '0.5');
                    } else {
                        $item.removeClass('disabled').css('pointer-events', '').css('opacity', '');
                    }
                });
                $('#pc-builder-menu .category').each(function () {
                    var $cat = $(this);
                    if ($cat.data('group') !== initialMenu) {
                        $cat.find('button').prop('disabled', true);
                    } else {
                        $cat.find('button').prop('disabled', false);
                    }
                });
            }
        }

        function refreshLoadedCategories(options) {
            options = options || {};
            var skipCatId = options.skipCatId;
            var renderOptions = options.renderOptions || {};
            $('#pc-builder-menu .product-container').each(function () {
                var $container = $(this);
                if (!$container.data('loaded')) {
                    return;
                }
                var $cat = $container.closest('.category');
                var catId = $cat.data('category-id');
                if (
                    typeof skipCatId !== 'undefined' &&
                    parseInt(skipCatId, 10) === parseInt(catId, 10)
                ) {
                    return;
                }
                renderProducts($container, null, catId, renderOptions);
            });
        }

        function collapseAllCategories() {
            var hasBootstrap =
                typeof window !== 'undefined' &&
                window.bootstrap &&
                window.bootstrap.Collapse;
            $('#pc-builder-menu .collapse').each(function () {
                var el = this;
                if (hasBootstrap) {
                    var instance = window.bootstrap.Collapse.getOrCreateInstance(el, {
                        toggle: false,
                    });
                    instance.hide();
                } else if ($.fn.collapse) {
                    $(el).collapse('hide');
                } else {
                    $(el).removeClass('show');
                }
            });
            $('#pc-builder-menu .category .toggle-icon')
                .removeClass('fa-chevron-up')
                .addClass('fa-chevron-down');
        }

        showInitialGroup();

        $('#pc-builder-main-menu').on('click', '.main-menu-item', function () {
            if ($(this).hasClass('disabled')) {
                return;
            }
            var group = $(this).data('group');
            $('#pc-builder-main-menu .main-menu-item').removeClass('active');
            $(this).addClass('active');
            $('#pc-builder-menu .category').each(function () {
                var $cat = $(this);
                if ($cat.data('group') === group) {
                    $cat.show();
                } else {
                    $cat.hide();
                }
            });
        });

        $('#collapse-categories').on('click', function () {
            collapseAllCategories();
        });

        $(document).off('keydown.pc_builder');
        $(document).on('keydown.pc_builder', function (event) {
            if (event.key === 'Escape' || event.key === 'Esc') {
                collapseAllCategories();
            }
        });

        function updateCategoryIndicators() {
            $('#pc-builder-menu .category').each(function () {
                var $cat = $(this);
                var cid = $cat.data('category-id');
                var $icon = $cat.find('.status-icon');
                if (shouldConsiderSelection(cid)) {
                    $icon.removeClass('fa-exclamation-circle text-warning')
                        .addClass('fa-check-circle text-success');
                } else {
                    $icon.removeClass('fa-check-circle text-success')
                        .addClass('fa-exclamation-circle text-warning');
                }
            });
        }

        function updateSummary() {
            var $list = $('#summary-list');
            $list.empty();
            var total = 0;
            var hasPendingPrice = false;
            var activeEntries = getActiveSelectionEntries();
            var visibleMap = {};
            activeEntries.forEach(function (entry) {
                var catId = entry.catId;
                var product = entry.product;
                var price = parsePriceValue(product.price);
                visibleMap[String(catId)] = true;
                var $item = $(
                    '<li class="list-group-item summary-item" data-cat-id="' + catId + '"></li>'
                );
                var $name = $('<span class="product-name"></span>').text(product.name);
                var isPendingPrice = isOutOfStockProduct(product);
                $item.append($name);
                if (isPendingPrice) {
                    $item.addClass('summary-out-of-stock');
                    var $badge = $(
                        '<span class="badge bg-warning text-dark ms-2">Bajo pedido</span>'
                    );
                    var $pendingLabel = $(
                        '<span class="pending-price text-muted ms-2">Por definir</span>'
                    );
                    $name.append($badge, $pendingLabel);
                    hasPendingPrice = true;
                } else {
                    var $price = $('<span class="product-price"></span>').text(
                        formatPriceDisplay(price)
                    );
                    $item.append($price);
                    total += price;
                }
                var $remove = $(
                    '<button class="btn btn-sm btn-outline-danger remove-item" title="Quitar">&times;</button>'
                );
                $item.append($remove);
                $list.append($item);
            });
            var $summaryTotal = $('#summary-total');
            if (hasPendingPrice) {
                if (total > 0) {
                    $summaryTotal.text(formatPriceDisplay(total) + ' + Por definir');
                } else {
                    $summaryTotal.text('Por definir');
                }
            } else {
                $summaryTotal.text(formatPriceDisplay(total));
            }

            var missing = [];
            $('#pc-builder-menu .category').each(function () {
                var $cat = $(this);
                var required = $cat.data('required') === 1;
                var cid = $cat.data('category-id');
                if (required && !visibleMap[String(cid)]) {
                    var name = $cat.find('button span').first().text().trim();
                    missing.push(name);
                }
            });
            var disabled = missing.length > 0;
            $('#add-to-cart').prop('disabled', disabled);
            $('#download-quote').prop('disabled', disabled);
            var $missing = $('#missing-required');
            if (missing.length) {
                $missing.text('Te hace falta agregar: ' + missing.join(', '));
            } else {
                $missing.text('');
            }
            updateCategoryIndicators();
            updateLockState();
            saveSelections();
        }

        function renderCategoryPagination(
            $container,
            totalItems,
            perPageSetting,
            currentPage,
            totalPages
        ) {
            var $pagination = $container.closest('.collapse').find('.category-pagination');
            if (!$pagination.length) {
                return;
            }
            if (!totalItems || !perPageSetting || perPageSetting <= 0) {
                $pagination.empty().addClass('d-none').removeAttr('data-category-id');
                return;
            }
            var catId = $container.closest('.category').data('category-id');
            $pagination
                .removeClass('d-none')
                .attr('data-category-id', catId)
                .empty();

            var $list = $('<ul class="pagination pagination-sm mb-0 justify-content-center"></ul>');
            for (var page = 1; page <= totalPages; page++) {
                var $item = $('<li class="page-item"></li>');
                if (page === currentPage) {
                    $item.addClass('active');
                }
                var $button = $('<button type="button" class="page-link"></button>')
                    .attr('data-page', page)
                    .text(page);
                if (page === currentPage) {
                    $button
                        .attr('aria-current', 'page')
                        .attr('aria-disabled', 'true')
                        .prop('disabled', true);
                }
                $item.append($button);
                $list.append($item);
            }
            $pagination.append($list);
        }

        function renderProducts($container, products, catId, options) {
            options = options || {};
            if (typeof options.searchTerm === 'string') {
                $container.data('searchTerm', options.searchTerm);
            }
            var searchTerm = getStoredSearchTerm($container).toLowerCase();
            var baseList;
            if (Array.isArray(products)) {
                baseList = products.slice();
                $container.data('products', baseList.slice());
            } else {
                var storedProducts = $container.data('products');
                baseList = Array.isArray(storedProducts) ? storedProducts.slice() : [];
            }

            var selectedIds = getComparableSelectedIds(catId);
            var shouldApplyCompatibility =
                showOnlyCompatibleProducts() &&
                selectedIds.length > 0 &&
                baseList.length > 0;

            var requestToken = Date.now() + Math.random();
            $container.data('renderToken', requestToken);

            var compatibilityPromise;
            if (shouldApplyCompatibility) {
                showLoadingSpinner($container);
                var productIds = baseList.map(function (prod) {
                    return prod.id;
                });
                compatibilityPromise = ajax
                    .jsonRpc('/pc_builder/filter_compatibility', 'call', {
                        product_ids: productIds,
                        selected_ids: selectedIds,
                    })
                    .then(
                        function (resp) {
                            return resp || {};
                        },
                        function () {
                            return {};
                        }
                    );
            } else {
                $container.empty();
                var deferred = $.Deferred();
                deferred.resolve({});
                compatibilityPromise = deferred.promise();
            }

            compatibilityPromise.then(function (resp) {
                if ($container.data('renderToken') !== requestToken) {
                    return;
                }

                hideLoadingSpinner($container);
                var compatibilityMap = resp && resp.compatibility ? resp.compatibility : null;
                var hasRules = !!(resp && resp.has_rules);
                var showOnlyCompat = showOnlyCompatibleProducts();

                var workingList = baseList.slice();
                if (hasRules && compatibilityMap && showOnlyCompat) {
                    workingList = workingList.filter(function (prod) {
                        var key = String(prod.id);
                        if (Object.prototype.hasOwnProperty.call(compatibilityMap, key)) {
                            return compatibilityMap[key];
                        }
                        if (Object.prototype.hasOwnProperty.call(compatibilityMap, prod.id)) {
                            return compatibilityMap[prod.id];
                        }
                        return true;
                    });
                }

                var showOutOfStock = showOutOfStockProducts();
                var sortedProducts = workingList
                    .map(function (prod, index) {
                        return { product: prod, index: index };
                    })
                    .sort(function (a, b) {
                        var stockA = parseStockValue(a.product.stock);
                        var stockB = parseStockValue(b.product.stock);
                        var outA = stockA !== null ? stockA <= 0 : false;
                        var outB = stockB !== null ? stockB <= 0 : false;
                        if (outA === outB) {
                            return a.index - b.index;
                        }
                        return outA ? 1 : -1;
                    })
                    .map(function (entry) {
                        return entry.product;
                    })
                    .filter(function (prod) {
                        if (!searchTerm) {
                            return true;
                        }
                        var name = typeof prod.name === 'string' ? prod.name.toLowerCase() : '';
                        return name.indexOf(searchTerm) !== -1;
                    });

                var filteredProducts = [];
                sortedProducts.forEach(function (prod) {
                    var stockValue = parseStockValue(prod.stock);
                    var outOfStock = stockValue !== null ? stockValue <= 0 : false;
                    var isSelected = selections[catId] && selections[catId].id === prod.id;
                    if (isSelected) {
                        selections[catId].stock = stockValue;
                        selections[catId].price = parsePriceValue(prod.price);
                    }
                    if (!showOutOfStock && outOfStock) {
                        return;
                    }
                    filteredProducts.push({
                        product: prod,
                        stockValue: stockValue,
                        outOfStock: outOfStock,
                        isSelected: isSelected,
                    });
                });

                var totalItems = filteredProducts.length;
                var perPageSetting = getMaxProductsPerCategory();
                var perPage = perPageSetting && perPageSetting > 0 ? perPageSetting : totalItems || 1;
                if (perPage <= 0) {
                    perPage = totalItems || 1;
                }
                var totalPages = perPage > 0 ? Math.ceil(totalItems / perPage) : 1;
                if (!totalPages) {
                    totalPages = 1;
                }
                var storedPage = parseInt($container.data('currentPage'), 10);
                var currentPage = !isNaN(storedPage) && storedPage > 0 ? storedPage : 1;
                if (options.resetPage === true) {
                    currentPage = 1;
                }
                if (typeof options.page === 'number' && !isNaN(options.page)) {
                    currentPage = options.page;
                }
                if (currentPage > totalPages) {
                    currentPage = totalPages;
                }
                if (currentPage < 1) {
                    currentPage = 1;
                }
                $container.data('currentPage', currentPage);

                renderCategoryPagination($container, totalItems, perPageSetting, currentPage, totalPages);

                if (!totalItems) {
                    $container.empty();
                    $container.append(
                        '<div class="col-12 no-results">No se encontraron productos disponibles.</div>'
                    );
                    return;
                }

                $container.empty();
                var startIndex = (currentPage - 1) * perPage;
                var pageProducts = filteredProducts.slice(startIndex, startIndex + perPage);

                pageProducts.forEach(function (entry) {
                    var prod = entry.product;
                    var stockValue = entry.stockValue;
                    var outOfStock = entry.outOfStock;
                    var isSelected = entry.isSelected;
                    var $col = $('<div class="col-6 col-md-4 mb-2"></div>');
                    var $card = $('<div class="card product-card h-100"></div>');
                    if (outOfStock) {
                        $card.addClass('out-of-stock');
                    }
                    $card.append('<img class="card-img-top" src="' + prod.image_url + '"/>');
                    var $body = $('<div class="card-body p-2 text-center"></div>');
                    $body.append('<div class="card-title small mb-1">' + prod.name + '</div>');
                    if (outOfStock) {
                        $body.append('<span class="badge bg-warning text-dark w-100">Bajo pedido</span>');
                    } else {
                        var priceNumber = parsePriceValue(prod.price);
                        $body.append(
                            '<div class="card-text font-weight-bold">' +
                            formatPriceDisplay(priceNumber) +
                            '</div>'
                        );
                    }
                    $card.append($body);
                    if (isSelected) {
                        $card.addClass('selected');
                    }

                    $col.append($card);

                    $card.on('click', function () {
                        if ($card.hasClass('selected')) {
                            $card.removeClass('selected');
                            delete selections[catId];
                            updateSummary();
                            hideAlert();
                            refreshLoadedCategories({ skipCatId: catId });
                            return;
                        }
                        var selectedIdsForCheck = getComparableSelectedIds(catId);
                        ajax
                            .jsonRpc('/pc_builder/check_compatibility', 'call', {
                                product_id: prod.id,
                                selected_ids: selectedIdsForCheck,
                            })
                            .then(function (resp) {
                                if (resp.compatible) {
                                    $container.find('.product-card').removeClass('selected');
                                    $card.addClass('selected');
                                    selections[catId] = {
                                        id: prod.id,
                                        name: prod.name,
                                        price: parsePriceValue(prod.price),
                                        stock: stockValue,
                                    };
                                    updateSummary();
                                    hideAlert();
                                    refreshLoadedCategories({ skipCatId: catId });
                                } else {
                                    showAlert(resp.message);
                                }
                            });
                    });

                    $container.append($col);
                });
            });
        }

        $('#pc-builder-menu').on('input', '.category-search', function () {
            var $input = $(this);
            var term = ($input.val() || '').toString();
            var searchTerm = term.trim();
            var $collapse = $input.closest('.collapse');
            var $container = $collapse.find('.product-container');
            var $cat = $collapse.closest('.category');
            var catId = $cat.data('category-id');
            $container.data('searchTerm', searchTerm);
            if ($container.data('loaded')) {
                renderProducts($container, null, catId, {
                    searchTerm: searchTerm,
                    resetPage: true,
                });
            }
        });

        $('#pc-builder-menu').on('click', '.category-pagination .page-link', function (event) {
            event.preventDefault();
            var $link = $(this);
            var page = parseInt($link.attr('data-page'), 10);
            if (isNaN(page) || page < 1) {
                return;
            }
            var $pagination = $link.closest('.category-pagination');
            var $cat = $pagination.closest('.category');
            var catId = $cat.data('category-id');
            var $container = $cat.find('.product-container');
            if (!$container.length || !$container.data('loaded')) {
                return;
            }
            renderProducts($container, null, catId, { page: page });
        });

        $('#toggle-out-of-stock').on('change', function () {
            refreshLoadedCategories({ renderOptions: { resetPage: true } });
            updateSummary();
        });

        $('#max-products-per-category').on('input', function () {
            refreshLoadedCategories({ renderOptions: { resetPage: true } });
        });

        $('#toggle-compatible-only').on('change', function () {
            refreshLoadedCategories({ renderOptions: { resetPage: true } });
        });

        $('#pc-builder-menu .collapse')
            .on('show.bs.collapse', function () {
                var $collapse = $(this);
                var $cat = $collapse.closest('.category');
                var catId = $cat.data('category-id');
                var $container = $collapse.find('.product-container');
                var searchTerm = ($collapse.find('.category-search').val() || '').toString().trim();
                $container.data('searchTerm', searchTerm);
                $cat.find('.toggle-icon').removeClass('fa-chevron-down').addClass('fa-chevron-up');

                if ($container.data('loaded')) {
                    return;
                }

                showLoadingSpinner($container);

                ajax.post('/pc_builder/search', { category_id: catId }).then(
                    function (products) {
                        hideLoadingSpinner($container);
                        renderProducts($container, products, catId, {
                            searchTerm: searchTerm,
                            resetPage: true,
                        });
                        $container.data('loaded', true);
                        updateSummary();
                    },
                    function () {
                        hideLoadingSpinner($container);
                        $container.append(
                            '<div class="col-12"><div class="alert alert-danger" role="alert">No fue posible cargar los productos.</div></div>'
                        );
                    }
                );
            })
            .on('hide.bs.collapse', function () {
                $(this)
                    .closest('.category')
                    .find('.toggle-icon')
                    .removeClass('fa-chevron-up')
                    .addClass('fa-chevron-down');
            });

        $('#summary-list').on('click', '.remove-item', function () {
            var catId = $(this).closest('li').data('cat-id');
            delete selections[catId];
            $('#pc-builder-menu .category[data-category-id="' + catId + '"] .product-card.selected').removeClass('selected');
            updateSummary();
            hideAlert();
            refreshLoadedCategories({ skipCatId: catId });
        });

        $('#reset-builder').on('click', function () {
            selections = {};
            $('#pc-builder-menu .product-card').removeClass('selected');
            updateSummary();
            hideAlert();
            localStorage.removeItem(storageKey);
            refreshLoadedCategories({ renderOptions: { resetPage: true } });
        });

        $('#add-to-cart').on('click', function () {
            var product_ids = $.map(getActiveProducts(), function (prod) {
                return prod.id;
            });
            if (!product_ids.length) {
                return;
            }
            ajax
                .jsonRpc('/pc_builder/add_to_cart', 'call', { product_ids: product_ids })
                .then(function () {
                    window.location.href = '/shop/cart';
                });
        });

        function validatePublicFields() {
            var name = $('#visitor-name').val().trim();
            var phone = $('#phone-extension').val() + $('#visitor-phone').val().trim();
            var valid =
                name &&
                $('#visitor-phone').val().trim() &&
                /^\+\d+$/.test(phone);
            $('#public-required-msg').toggleClass('d-none', valid);
            return valid;
        }

        function updateFlag() {
            var flag = $('#phone-extension option:selected').data('flag');
            if (flag) {
                $('#phone-flag').attr('src', '/website_pages_constructor/static/description/' + flag + '.png');
            }
        }

        $('#visitor-name, #visitor-phone, #phone-extension').on('input change', validatePublicFields);
        $('#phone-extension').on('change', updateFlag);

        $('#download-quote').on('click', function () {
            var product_ids = $.map(getActiveProducts(), function (prod) {
                return prod.id;
            });
            if (!product_ids.length) {
                return;
            }
            if (isPublic) {
                $('#public-fields').removeClass('d-none');
                validatePublicFields();
                return;
            }
            var url = '/pc_builder/quote?product_ids=' + product_ids.join(',');
            window.open(url, '_blank');
        });

        $('#confirm-download').on('click', function () {
            var product_ids = $.map(getActiveProducts(), function (prod) {
                return prod.id;
            });
            if (!product_ids.length) {
                return;
            }
            if (!validatePublicFields()) {
                return;
            }
            var name = $('#visitor-name').val().trim();
            var phone =
                $('#phone-extension').val() + $('#visitor-phone').val().trim();
            var url =
                '/pc_builder/quote?product_ids=' +
                product_ids.join(',') +
                '&name=' + encodeURIComponent(name) +
                '&phone=' + encodeURIComponent(phone);
            window.open(url, '_blank');
        });

        $('#contact-advisor').on('click', function () {
            var product_ids = $.map(getActiveProducts(), function (prod) {
                return prod.id;
            });
            if (!product_ids.length) {
                return;
            }
            var url = '/pc_builder/quote?product_ids=' + product_ids.join(',');
            if (isPublic) {
                if ($('#public-fields').hasClass('d-none')) {
                    $('#public-fields').removeClass('d-none');
                    validatePublicFields();
                    return;
                }
                if (!validatePublicFields()) {
                    return;
                }
                var name = $('#visitor-name').val().trim();
                var phone =
                    $('#phone-extension').val() + $('#visitor-phone').val().trim();
                url +=
                    '&name=' + encodeURIComponent(name) +
                    '&phone=' + encodeURIComponent(phone);
            }
            var message =
                'Buenas! deseo recibir más información sobre esta cotización';
            var whatsappUrl =
                'https://wa.me/573142454843?text=' +
                encodeURIComponent(message + ' ' + window.location.origin + url);
            window.open(whatsappUrl, '_blank');
        });
        updateFlag();
        updateSummary();
        updateLockState();
        hidePageLoader();
    });
});

