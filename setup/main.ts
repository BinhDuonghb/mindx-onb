import { defineAppSetup } from '@slidev/types';

export default defineAppSetup(({ app, router }) => {
    // Custom setup for the app
    // You can add global components, plugins, etc. here

    // Example: Add a global property
    app.config.globalProperties.$customBrand = 'MindX Engineer Onboarding';

    // Example: Add custom router guards
    router.beforeEach((to, from, next) => {
        // Custom navigation logic if needed
        next();
    });

    // Example: Register global components
    // app.component('CustomComponent', CustomComponent);
});
