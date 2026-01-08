// Dark mode support for Plotly graphs and Dash components
(function() {
    // Function to get CSS variable value
    function getCSSVariable(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    // Function to apply theme to page elements
    function applyThemeToPage() {
        const bgPrimary = getCSSVariable('--bg-primary');
        const textPrimary = getCSSVariable('--text-primary');

        // Force body and main containers
        document.body.style.backgroundColor = bgPrimary;
        document.body.style.color = textPrimary;

        // Force all Dash core containers
        const dashContainers = document.querySelectorAll('#react-entry-point, #page-content, .main-content, [data-dash-is-loading]');
        dashContainers.forEach(el => {
            el.style.backgroundColor = bgPrimary;
            el.style.color = textPrimary;
        });
    }

    // Function to update all Plotly graphs for current theme
    function updatePlotlyGraphs() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        // Get theme colors
        const bgPrimary = getCSSVariable('--bg-primary');
        const bgSecondary = getCSSVariable('--bg-secondary');
        const gridColor = getCSSVariable('--border-default');
        const textColor = getCSSVariable('--text-primary');

        // Find all plotly graphs
        const graphs = document.querySelectorAll('.js-plotly-plot');

        graphs.forEach(graph => {
            if (graph && graph.layout) {
                const update = {
                    'paper_bgcolor': bgSecondary,
                    'plot_bgcolor': bgPrimary,
                    'font.color': textColor,
                    'xaxis.gridcolor': gridColor,
                    'yaxis.gridcolor': gridColor,
                    'xaxis.color': textColor,
                    'yaxis.color': textColor,
                    'xaxis.tickfont.color': textColor,
                    'yaxis.tickfont.color': textColor,
                    'legend.font.color': textColor
                };

                // Also update annotations if present
                if (graph.layout.annotations) {
                    graph.layout.annotations.forEach((ann, idx) => {
                        update[`annotations[${idx}].font.color`] = textColor;
                    });
                }

                // Update the graph
                try {
                    Plotly.relayout(graph, update);
                } catch (e) {
                    console.log('Could not update graph:', e);
                }
            }
        });
    }

    // Function to apply full theme
    function applyFullTheme() {
        applyThemeToPage();
        setTimeout(updatePlotlyGraphs, 200);
    }

    // Update on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(applyFullTheme, 500);
        });
    } else {
        setTimeout(applyFullTheme, 500);
    }

    // Watch for theme changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'data-theme') {
                setTimeout(applyFullTheme, 100);
            }
        });
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });

    // Watch for new Dash content
    const contentObserver = new MutationObserver(function(mutations) {
        let hasNewGraphs = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.classList && (node.classList.contains('js-plotly-plot') || node.querySelector('.js-plotly-plot'))) {
                        hasNewGraphs = true;
                    }
                });
            }
        });
        if (hasNewGraphs) {
            setTimeout(applyFullTheme, 300);
        }
    });

    // Observe the main content area for changes
    setTimeout(function() {
        const mainContent = document.querySelector('#page-content') || document.body;
        contentObserver.observe(mainContent, {
            childList: true,
            subtree: true
        });
    }, 1000);

    // Re-apply theme periodically to catch any Dash updates
    setInterval(applyThemeToPage, 2000);
})();
