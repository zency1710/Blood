// Blood Bank Management System - JavaScript

// Global State
let currentPage = 'home';
let currentAdminTab = 'requests';
let currentUserTab = 'profile';
let isAdminLoggedIn = false;
let isUserLoggedIn = false;
let currentUser = null;

// API base URL for backend when serving frontend on a different port
const API_BASE = 'http://127.0.0.1:5000';

// Patch fetch to automatically prefix API calls with backend base URL
// This avoids 404/HTML responses from the static server on port 8000
const _origFetch = window.fetch.bind(window);
window.fetch = (url, options) => {
    try {
        if (typeof url === 'string' && url.startsWith('/api')) {
            url = `${API_BASE}${url}`;
        }
    } catch (e) {
        // Fall back to original URL on any unexpected error
    }
    return _origFetch(url, options);
};

// Utility Functions
function generateId() {
    return 'id-' + Math.random().toString(36).substr(2, 16);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

// Toast Notification System
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = toast.querySelector('.toast-message');

    toast.className = `toast ${type}`;
    toastMessage.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        hideToast();
    }, 5000);
}

function hideToast() {
    const toast = document.getElementById('toast');
    toast.classList.remove('show');
}

// Navigation Functions
function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Show selected page
    document.getElementById(pageId).classList.add('active');
    currentPage = pageId;

    // Update navigation active state
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });

    // Find and activate current nav link
    const currentNavLink = Array.from(document.querySelectorAll('.nav-link')).find(link => {
        const onclick = link.getAttribute('onclick');
        return onclick && onclick.includes(`'${pageId}'`);
    });

    if (currentNavLink) {
        currentNavLink.classList.add('active');
    }

    // Close mobile menu if open
    const navMenu = document.getElementById('nav-menu');
    const hamburger = document.getElementById('hamburger');
    navMenu.classList.remove('active');
    hamburger.classList.remove('active');

    // Special handling for admin dashboard
    if (pageId === 'admin-dashboard') {
        if (!isAdminLoggedIn) {
            showPage('admin-login');
            showToast('Please login to access admin dashboard', 'error');
            return;
        }
        loadAdminDashboard();
    }

    // Special handling for user dashboard
    if (pageId === 'user-dashboard') {
        if (!isUserLoggedIn) {
            showPage('login');
            showToast('Please login to access your dashboard', 'error');
            return;
        }
        loadUserDashboard();
    }

    if (pageId === 'donor-registration' || pageId === 'request-blood') {
        updateFormButtons();
    }

    // Load page-specific data
    switch (pageId) {
        case 'home':
            loadBloodAvailability();
            updateHomeStats();
            break;
        case 'admin-dashboard':
            if (isAdminLoggedIn) {
                loadAdminDashboard();
            }
            break;
        case 'user-dashboard':
            if (isUserLoggedIn) {
                loadUserDashboard();
            }
            break;
    }
}

// Mobile Menu Toggle
function toggleMobileMenu() {
    const navMenu = document.getElementById('nav-menu');
    const hamburger = document.getElementById('hamburger');

    navMenu.classList.toggle('active');
    hamburger.classList.toggle('active');
}

// Password Toggle
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const button = input.parentElement.querySelector('.password-toggle i');

    if (input.type === 'password') {
        input.type = 'text';
        button.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        button.className = 'fas fa-eye';
    }
}

// Login Tab Switching
function switchLoginTab(type) {
    // Remove active class from all tabs
    document.querySelectorAll('.login-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active-form class from all forms
    document.querySelectorAll('.login-form').forEach(form => {
        form.classList.remove('active-form');
    });
    
    // Add active class to clicked tab
    event.target.closest('.login-tab').classList.add('active');
    
    // Show corresponding form
    if (type === 'user') {
        document.getElementById('user-login-form').classList.add('active-form');
    } else if (type === 'admin') {
        document.getElementById('admin-login-form').classList.add('active-form');
    }
}

// Home Page Functions
async function loadBloodAvailability() {
    const availabilityContainer = document.getElementById('blood-availability');
    if (!availabilityContainer) return;

    try {
        const response = await fetch('/api/donors');
        const donors = await response.json();
        const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
        availabilityContainer.innerHTML = '';

        bloodGroups.forEach(group => {
            const count = donors.filter(donor => donor.blood_group === group).length;
            const groupCard = document.createElement('div');
            groupCard.className = 'blood-group-card';
            groupCard.innerHTML = `
                <div class="blood-badge">${group}</div>
                <div class="blood-count">${count}</div>
                <div class="blood-label">Donors</div>
            `;
            availabilityContainer.appendChild(groupCard);
        });
    } catch (error) {
        console.error('Error loading blood availability:', error);
        showToast('Failed to load blood availability', 'error');
    }
}

async function updateHomeStats() {
    const totalDonorsElement = document.getElementById('total-donors');
    if (totalDonorsElement) {
        try {
            const response = await fetch('/api/donors');
            const donors = await response.json();
            totalDonorsElement.textContent = donors.length;
        } catch (error) {
            console.error('Error updating home stats:', error);
        }
    }
}


// Donor Registration Functions
function initializeDonorForm() {
    const donorForm = document.getElementById('donor-form');
    if (!donorForm) return;

    donorForm.addEventListener('submit', handleDonorRegistration);
}

async function handleDonorRegistration(event) {
    event.preventDefault();

    // Check if user is logged in, if not redirect to sign in page
    if (!isUserLoggedIn || !currentUser) {
        showToast('Please sign in to register as a donor', 'error');
        showPage('login');
        return;
    }

    const formData = new FormData(event.target);
    const donorData = {
        name: formData.get('name'),
        age: parseInt(formData.get('age')),
        blood_group: formData.get('bloodGroup'),
        city: formData.get('city'),
        contact: formData.get('contact'),
        email: formData.get('email') || '',
        last_donation_date: null
    };

    if (!validateDonorData(donorData)) {
        return;
    }

    try {
        // First register the donor
        const response = await fetch('/api/donors', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(donorData),
        });

        if (response.ok) {
            const donor = await response.json();

            // Add this as a donation to user's history (user is logged in due to our check)
            try {
                // Add donation to user's history
                const donationData = {
                    blood_group: donorData.blood_group,
                    donation_date: new Date().toISOString().split('T')[0], // Today's date
                    location: donorData.city,
                    units_donated: 1, // Default 1 unit for new registration
                    notes: 'Initial donor registration'
                };

                const donationResponse = await fetch(`/api/users/${currentUser.id}/donations`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(donationData),
                });

                if (donationResponse.ok) {
                    console.log('Donation added to user history');
                }
            } catch (donationError) {
                console.error('Error adding donation to user history:', donationError);
                // Continue with success message even if donation history fails
            }

            // Success UI updates
            showToast('Registration successful! Thank you for becoming a donor.');
            event.target.reset();
            updateHomeStats();
            loadBloodAvailability();

            // Refresh user dashboard
            loadUserDashboard();
        } else {
            showToast('Registration failed. Please try again.', 'error');
        }
    } catch (error) {
        console.error('Error during donor registration:', error);
        showToast('An error occurred. Please try again.', 'error');
    }
}

function validateDonorData(data) {
    if (!data.name.trim()) {
        showToast('Name is required', 'error');
        return false;
    }

    if (data.age < 18 || data.age > 65) {
        showToast('Age must be between 18 and 65', 'error');
        return false;
    }

    if (!data.blood_group) {
        showToast('Blood group is required', 'error');
        return false;
    }

    if (!data.city.trim()) {
        showToast('City is required', 'error');
        return false;
    }

    if (!data.contact.trim()) {
        showToast('Contact number is required', 'error');
        return false;
    }

    if (data.contact.length < 10) {
        showToast('Contact number must be at least 10 digits', 'error');
        return false;
    }

    if (data.email && !/\S+@\S+\.\S+/.test(data.email)) {
        showToast('Please enter a valid email address', 'error');
        return false;
    }

    return true;
}

// Blood Request Functions
function initializeRequestForm() {
    const requestForm = document.getElementById('request-form');
    if (!requestForm) return;

    requestForm.addEventListener('submit', handleBloodRequest);
}

async function handleBloodRequest(event) {
    event.preventDefault();

    // Check if user is logged in, if not redirect to sign in page
    if (!isUserLoggedIn || !currentUser) {
        showToast('Please sign in to submit a blood request', 'error');
        showPage('login');
        return;
    }

    const formData = new FormData(event.target);
    const requestData = {
        patient_name: formData.get('requesterName'),
        requesterType: formData.get('requesterType'), // This field is not in the DB schema, but we keep it for validation
        blood_group: formData.get('bloodGroup'),
        urgencyLevel: formData.get('urgencyLevel'), // Also not in DB schema
        city: formData.get('city'),
        contact: formData.get('contact'),
        email: formData.get('email') || '',
        units: parseInt(formData.get('unitsNeeded')),
        hospital: 'N/A' // Assuming hospital might not always be provided
    };

    if (!validateRequestData(requestData)) {
        return;
    }
    
    // Adjust for hospital/patient name
    if (requestData.requesterType === 'hospital') {
        requestData.hospital = requestData.patient_name;
    }

    try {
        // First, submit the blood request to the main requests table
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        });

        if (response.ok) {
            const result = await response.json();
            showToast('Blood request submitted successfully! We will contact you soon.');
            
            // Add this request to user's history (user is logged in due to our check)
            try {
                const userRequestData = {
                    request_id: result.id, // Use the ID from the main request
                    patient_name: requestData.patient_name,
                    blood_group: requestData.blood_group,
                    units_requested: requestData.units,
                    hospital: requestData.hospital,
                    city: requestData.city,
                    contact: requestData.contact,
                    urgency_level: requestData.urgencyLevel
                };
                
                const userResponse = await fetch(`/api/users/${currentUser.id}/requests`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(userRequestData),
                });

                if (userResponse.ok) {
                    console.log('Request added to user history successfully');
                } else {
                    console.error('Failed to add request to user history');
                }
            } catch (userError) {
                console.error('Error adding request to user history:', userError);
            }
            
            // Refresh user dashboard if currently viewing
            if (currentPage === 'user-dashboard') {
                loadUserDashboard();
            }
            
            event.target.reset();
        } else {
            showToast('Failed to submit blood request. Please try again.', 'error');
        }
    } catch (error) {
        console.error('Error submitting blood request:', error);
        showToast('An error occurred. Please try again.', 'error');
    }
}


function validateRequestData(data) {
    if (!data.patient_name.trim()) {
        showToast('Requester name is required', 'error');
        return false;
    }

    if (!data.requesterType) {
        showToast('Requester type is required', 'error');
        return false;
    }

    if (!data.blood_group) {
        showToast('Blood group is required', 'error');
        return false;
    }

    if (!data.urgencyLevel) {
        showToast('Urgency level is required', 'error');
        return false;
    }

    if (!data.city.trim()) {
        showToast('City is required', 'error');
        return false;
    }

    if (!data.contact.trim()) {
        showToast('Contact number is required', 'error');
        return false;
    }

    if (data.contact.length < 10) {
        showToast('Contact number must be at least 10 digits', 'error');
        return false;
    }

    if (data.email && !/\S+@\S+\.\S+/.test(data.email)) {
        showToast('Please enter a valid email address', 'error');
        return false;
    }

    if (!data.units || data.units < 1) {
        showToast('Units needed must be at least 1', 'error');
        return false;
    }

    return true;
}


// Admin Functions
function initializeAdminLogin() {
    const adminForm = document.getElementById('admin-login-form');
    if (!adminForm) return;

    adminForm.addEventListener('submit', handleAdminLogin);
}

async function handleAdminLogin(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const username = formData.get('username');
    const password = formData.get('password');

    try {
        const response = await fetch('/api/admin/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (response.ok) {
            isAdminLoggedIn = true;
            localStorage.setItem('bloodbank_admin_session', 'true');
            showToast('Login successful! Redirecting to dashboard...');

            setTimeout(() => {
                showPage('admin-dashboard');
            }, 1000);
        } else {
            showToast('Invalid username or password', 'error');
        }
    } catch (error) {
        console.error('Admin login error:', error);
        showToast('An error occurred during login.', 'error');
    }
}


function adminLogout() {
    isAdminLoggedIn = false;
    localStorage.removeItem('bloodbank_admin_session');
    showToast('Logged out successfully');
    showPage('home');
}

function loadAdminDashboard() {
    updateAdminStats();
    showAdminTab(currentAdminTab);
}

async function updateAdminStats() {
    try {
        const [donorsRes, requestsRes] = await Promise.all([
            fetch('/api/donors'),
            fetch('/api/requests')
        ]);
        const donors = await donorsRes.json();
        const requests = await requestsRes.json();
        
        const totalDonors = donors.length;
        const totalRequests = requests.length;
        const pendingRequests = requests.filter(req => req.status === 'pending').length;
        const fulfilledRequests = requests.filter(req => req.status === 'fulfilled').length;

        document.getElementById('admin-total-donors').textContent = totalDonors;
        document.getElementById('admin-total-requests').textContent = totalRequests;
        document.getElementById('admin-pending-requests').textContent = pendingRequests;
        document.getElementById('admin-fulfilled-requests').textContent = fulfilledRequests;
    } catch (error) {
        console.error('Error updating admin stats:', error);
    }
}


function showAdminTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Show selected tab
    document.querySelector(`[onclick="showAdminTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`admin-${tabName}-tab`).classList.add('active');

    currentAdminTab = tabName;

    // Load tab content
    if (tabName === 'requests') {
        loadRequestsList();
    } else if (tabName === 'donors') {
        loadDonorsList();
    }
}

async function loadRequestsList() {
    const container = document.getElementById('requests-list');
    if (!container) return;

    try {
        const response = await fetch('/api/requests');
        const requests = await response.json();
        container.innerHTML = '';

        if (requests.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No blood requests found</p>';
            return;
        }

        requests.forEach(request => {
            const requestCard = createRequestCard(request);
            container.appendChild(requestCard);
        });
    } catch (error) {
        console.error('Error loading requests list:', error);
        container.innerHTML = '<p style="text-align: center; color: #dc2626; padding: 2rem;">Failed to load requests.</p>';
    }
}

function createRequestCard(request) {
    const card = document.createElement('div');
    // A default for urgencyLevel since it's not in the DB.
    const urgencyLevel = request.urgencyLevel || 'normal';
    card.className = `request-card ${urgencyLevel === 'critical' ? 'urgency-critical' : ''}`;

    const statusClass = `status-${request.status}`;
    const urgencyClass = `urgency-${urgencyLevel}`;

    let actionButtons = '';
    if (request.status === 'pending') {
        actionButtons = `
            <button class="btn btn-approve" onclick="updateRequestStatus(${request.id}, 'approved')">
                <i class="fas fa-check-circle"></i> Approve
            </button>
            <button class="btn btn-reject" onclick="updateRequestStatus(${request.id}, 'rejected')">
                <i class="fas fa-times-circle"></i> Reject
            </button>
        `;
    } else if (request.status === 'approved') {
        actionButtons = `
            <button class="btn btn-fulfill" onclick="updateRequestStatus(${request.id}, 'fulfilled')">
                Mark Fulfilled
            </button>
        `;
    }

    card.innerHTML = `
        <div class="request-header">
            <div class="request-info">
                <h3>${request.patient_name}</h3>
                <p>${request.hospital}</p>
                <p>${request.city}</p>
            </div>
            <div class="blood-group-info">
                <div class="mini-blood-badge">${request.blood_group}</div>
                <div>
                    <span style="font-weight: 600;">${request.units} units</span>
                    <p class="urgency-badge ${urgencyClass}">${urgencyLevel} Priority</p>
                </div>
            </div>
            <div class="contact-info">
                <p>${request.contact}</p>
                ${request.email ? `<p>${request.email}</p>` : ''}
                <p style="font-size: 0.75rem; color: #6b7280;">${formatDate(new Date(request.created_at))}</p>
            </div>
            <div class="request-actions">
                <div class="status-badge ${statusClass}">${request.status}</div>
                ${actionButtons}
            </div>
        </div>
    `;

    return card;
}

async function updateRequestStatus(requestId, newStatus) {
    try {
        const response = await fetch(`/api/requests/${requestId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: newStatus }),
        });

        if (response.ok) {
            showToast(`Request ${newStatus} successfully!`);
            updateAdminStats();
            loadRequestsList();
        } else {
            showToast('Failed to update request status.', 'error');
        }
    } catch (error) {
        console.error('Error updating request status:', error);
        showToast('An error occurred while updating status.', 'error');
    }
}

async function loadDonorsList() {
    const container = document.getElementById('donors-list');
    if (!container) return;

    try {
        const response = await fetch('/api/donors');
        const donors = await response.json();
        container.innerHTML = '';

        if (donors.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No donors found</p>';
            return;
        }

        const donorsGrid = document.createElement('div');
        donorsGrid.className = 'donors-grid';

        donors.forEach(donor => {
            const donorCard = createDonorCard(donor);
            donorsGrid.appendChild(donorCard);
        });

        container.appendChild(donorsGrid);
    } catch (error) {
        console.error('Error loading donors list:', error);
        container.innerHTML = '<p style="text-align: center; color: #dc2626; padding: 2rem;">Failed to load donors.</p>';
    }
}


function createDonorCard(donor) {
    const card = document.createElement('div');
    card.className = 'donor-card';

    card.innerHTML = `
        <div class="donor-header">
            <div class="mini-blood-badge">${donor.blood_group}</div>
            <div class="donor-info">
                <h3>${donor.name}</h3>
                <p>Age: ${donor.age}</p>
                <p>${donor.city}</p>
                <p>${donor.contact}</p>
                ${donor.email ? `<p>${donor.email}</p>` : ''}
            </div>
        </div>
        <div class="donor-details">
            <p>Registered: ${donor.registrationDate ? formatDate(new Date(donor.registrationDate)) : 'N/A'}</p>
            ${donor.last_donation_date ?
                `<p>Last Donation: ${formatDate(new Date(donor.last_donation_date))}</p>` :
                '<p>No donations recorded</p>'
            }
        </div>
    `;

    return card;
}


// Form Initialization Functions
function initializeUserLogin() {
    const loginForm = document.getElementById('user-login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(loginForm);
            const username = formData.get('username');
            const password = formData.get('password');
            const rememberMe = formData.get('rememberMe');
            
            const success = await userLogin(username, password);
            if (success) {
                if (rememberMe) {
                    localStorage.setItem('rememberUser', 'true');
                    localStorage.setItem('rememberedUsername', username);
                }
                loginForm.reset();
            }
        });
    }
}

function initializeUserRegister() {
    const registerForm = document.getElementById('user-register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(registerForm);
            const userData = {
                name: formData.get('name'),
                username: formData.get('username'),
                email: formData.get('email'),
                password: formData.get('password'),
                confirmPassword: formData.get('confirmPassword'),
                contact: formData.get('contact'),
                agreeTerms: formData.get('agreeTerms')
            };
            
            const success = await userRegister(userData);
            if (success) {
                registerForm.reset();
            }
        });
    }
}

// Initialize Application
function initializeApp() {
    // Check admin session
    if (localStorage.getItem('bloodbank_admin_session') === 'true') {
        isAdminLoggedIn = true;
    }

    // Check user session
    if (localStorage.getItem('isUserLoggedIn') === 'true') {
        isUserLoggedIn = true;
        currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
        if (currentUser) {
            updateNavigationForUser();
        }
    }

    // Initialize forms
    initializeDonorForm();
    initializeRequestForm();
    initializeAdminLogin();
    initializeUserLogin();
    initializeUserRegister();

    // Initialize mobile menu
    const hamburger = document.getElementById('hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', toggleMobileMenu);
    }

    // Load initial page data
    loadBloodAvailability();
    updateHomeStats();

    // Update form buttons based on login status
    updateFormButtons();

    // Show default page
    showPage('home');
}

// Close mobile menu when clicking on a link
document.addEventListener('click', function(event) {
    const navMenu = document.getElementById('nav-menu');
    const hamburger = document.getElementById('hamburger');

    if (event.target.matches('.nav-link')) {
        navMenu.classList.remove('active');
        hamburger.classList.remove('active');
    }
});

// Close toast when clicking outside
document.addEventListener('click', function(event) {
    const toast = document.getElementById('toast');
    if (!toast.contains(event.target) && toast.classList.contains('show')) {
        hideToast();
    }
});

// User Login Functions
async function userLogin(username, password) {
    try {
        const response = await fetch('/api/users/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            isUserLoggedIn = true;
            currentUser = data.user;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            localStorage.setItem('isUserLoggedIn', 'true');
            showToast('Login successful! Welcome back.', 'success');
            showPage('user-dashboard');
            updateNavigationForUser();
            updateFormButtons(); // Update form buttons after login
            return true;
        } else {
            showToast(data.error || 'Invalid username/email or password. Please try again.', 'error');
            return false;
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('An error occurred during login. Please try again.', 'error');
        return false;
    }
}

function userLogout() {
    isUserLoggedIn = false;
    currentUser = null;
    localStorage.removeItem('currentUser');
    localStorage.removeItem('isUserLoggedIn');
    
    // Hide notification icon
    const notifNavItem = document.getElementById('notification-nav-item');
    if (notifNavItem) {
        notifNavItem.style.display = 'none';
    }
    
    showToast('Logged out successfully.', 'success');
    showPage('home');
    updateNavigationForGuest();
    updateFormButtons(); // Update form buttons after logout
}

async function userRegister(userData) {
    // Validate password match
    if (userData.password !== userData.confirmPassword) {
        showToast('Passwords do not match. Please try again.', 'error');
        return false;
    }
    
    try {
        const requestBody = {
            name: userData.name,
            username: userData.username,
            email: userData.email,
            password: userData.password,
            contact: userData.contact,
            blood_group: ''
        };
        
        console.log('Registering user:', requestBody);
        
        const response = await fetch('/api/users/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
        });

        const data = await response.json();
        console.log('Registration response:', data);

        if (response.ok && data.success) {
            showToast('Account created successfully! You can now login.', 'success');
            showPage('login');
            return true;
        } else {
            showToast(data.error || 'Registration failed. Please try again.', 'error');
            return false;
        }
    } catch (error) {
        console.error('Registration error:', error);
        showToast('An error occurred during registration. Please try again.', 'error');
        return false;
    }
}

function updateNavigationForUser() {
    // Hide login button
    const loginNavItem = document.getElementById('login-nav-item');
    if (loginNavItem) {
        loginNavItem.style.display = 'none';
    }
    
    // Show profile icon
    const profileNavItem = document.getElementById('profile-nav-item');
    if (profileNavItem) {
        profileNavItem.style.display = 'block';
    }
    
    // Show notification icon
    const notifNavItem = document.getElementById('notification-nav-item');
    if (notifNavItem) {
        notifNavItem.style.display = 'block';
    }
}

function updateNavigationForGuest() {
    // Show login button
    const loginNavItem = document.getElementById('login-nav-item');
    if (loginNavItem) {
        loginNavItem.style.display = 'block';
    }
    
    // Hide profile icon
    const profileNavItem = document.getElementById('profile-nav-item');
    if (profileNavItem) {
        profileNavItem.style.display = 'none';
    }
    
    // Hide notification icon
    const notifNavItem = document.getElementById('notification-nav-item');
    if (notifNavItem) {
        notifNavItem.style.display = 'none';
    }
}

async function loadUserDashboard() {
    if (!isUserLoggedIn || !currentUser) return;
    
    // Update user name
    document.getElementById('user-name').textContent = currentUser.name;
    
    // Update profile information
    document.getElementById('profile-name').textContent = currentUser.name || 'N/A';
    document.getElementById('profile-email').textContent = currentUser.email || 'N/A';
    document.getElementById('profile-contact').textContent = currentUser.contact || 'N/A';
    
    try {
        // Fetch donations, requests, and notifications data
        const [donationsResponse, requestsResponse, notificationsResponse] = await Promise.all([
            fetch(`/api/users/${currentUser.id}/donations`),
            fetch(`/api/users/${currentUser.id}/requests`),
            fetch(`/api/users/${currentUser.id}/notifications`)
        ]);
        
        const donationsResult = await donationsResponse.json();
        const requestsResult = await requestsResponse.json();
        const notificationsResult = await notificationsResponse.json();
        
        const donations = donationsResult.donations || [];
        const requests = requestsResult.requests || [];
        
        // Update stats
        document.getElementById('user-total-donations').textContent = donations.length;
        document.getElementById('user-total-requests').textContent = requests.length;
        document.getElementById('user-lives-saved').textContent = donations.length * 3; // Each donation saves 3 lives
        
        // Update notification badge
        if (notificationsResult.unread_count !== undefined) {
            updateNotificationBadge(notificationsResult.unread_count);
        }
        
        // Calculate last donation
        if (donations.length > 0) {
            // Find the most recent donation
            const lastDonation = donations.reduce((latest, current) => {
                return new Date(current.donation_date) > new Date(latest.donation_date) ? current : latest;
            });
            const lastDonationDate = new Date(lastDonation.donation_date);
            const daysSince = Math.floor((new Date() - lastDonationDate) / (1000 * 60 * 60 * 24));
            document.getElementById('user-last-donation').textContent = `${daysSince} days ago`;
        } else {
            document.getElementById('user-last-donation').textContent = 'Never';
        }
        
    } catch (error) {
        console.error('Error loading user dashboard data:', error);
        // Fallback to 0 stats if there's an error
        document.getElementById('user-total-donations').textContent = '0';
        document.getElementById('user-total-requests').textContent = '0';
        document.getElementById('user-lives-saved').textContent = '0';
        document.getElementById('user-last-donation').textContent = 'Never';
    }
    
    // Load donations and requests
    loadUserDonations();
    loadUserRequests();
}

async function loadUserDonations() {
    const donationsList = document.getElementById('user-donations-list');
    
    if (!currentUser || !currentUser.id) {
        donationsList.innerHTML = '<div class="empty-state"><i class="fas fa-heart"></i><p>Please log in to view your donation history.</p></div>';
        return;
    }
    
    try {
        const response = await fetch(`/api/users/${currentUser.id}/donations`);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to load donations');
        }
        
        const donations = result.donations || [];
        
        if (donations.length === 0) {
            donationsList.innerHTML = '<div class="empty-state"><i class="fas fa-heart"></i><p>No donations yet. <a href="#" onclick="showPage(\'donor-registration\')">Register as a donor</a> to start saving lives!</p></div>';
            return;
        }
        
        donationsList.innerHTML = donations.map(donation => `
            <div class="donation-item">
                <div class="donation-header">
                    <div class="donation-title">Blood Donation</div>
                    <div class="donation-status status-completed">Completed</div>
                </div>
                <div class="donation-details">
                    <div class="detail-item">
                        <i class="fas fa-heart"></i>
                        <span>Blood Group: ${donation.blood_group}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-calendar"></i>
                        <span>Date: ${formatDate(new Date(donation.donation_date))}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>Location: ${donation.location}</span>
                    </div>
                    ${donation.units_donated ? `
                    <div class="detail-item">
                        <i class="fas fa-tint"></i>
                        <span>Units Donated: ${donation.units_donated}</span>
                    </div>
                    ` : ''}
                    ${donation.notes ? `
                    <div class="detail-item">
                        <i class="fas fa-sticky-note"></i>
                        <span>Notes: ${donation.notes}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading user donations:', error);
        donationsList.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Error loading donations. Please try again later.</p></div>';
    }
}

async function loadUserRequests() {
    const requestsList = document.getElementById('user-requests-list');
    
    if (!currentUser || !currentUser.id) {
        requestsList.innerHTML = '<div class="empty-state"><i class="fas fa-file-alt"></i><p>Please log in to view your request history.</p></div>';
        return;
    }
    
    try {
        const response = await fetch(`/api/users/${currentUser.id}/requests`);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to load requests');
        }
        
        const requests = result.requests || [];
        
        if (requests.length === 0) {
            requestsList.innerHTML = '<div class="empty-state"><i class="fas fa-file-alt"></i><p>No blood requests yet. <a href="#" onclick="showPage(\'request-blood\')">Submit a request</a> if you need blood!</p></div>';
            return;
        }
        
        requestsList.innerHTML = requests.map(request => `
            <div class="request-item">
                <div class="request-header">
                    <div class="request-title">Blood Request</div>
                    <div class="request-status status-${request.status}">${request.status}</div>
                </div>
                <div class="request-details">
                    <div class="detail-item">
                        <i class="fas fa-user"></i>
                        <span>Patient: ${request.patient_name}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-heart"></i>
                        <span>Blood Group: ${request.blood_group}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-calendar"></i>
                        <span>Date: ${formatDate(new Date(request.created_at))}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-tint"></i>
                        <span>Units Requested: ${request.units_requested}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-hospital"></i>
                        <span>Hospital: ${request.hospital}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>City: ${request.city}</span>
                    </div>
                    <div class="detail-item">
                        <i class="fas fa-phone"></i>
                        <span>Contact: ${request.contact}</span>
                    </div>
                    ${request.urgency_level !== 'normal' ? `
                    <div class="detail-item">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Urgency: ${request.urgency_level}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading user requests:', error);
        requestsList.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Error loading requests. Please try again later.</p></div>';
    }
}

function showUserTab(tabName) {
    // Hide all user tabs
    document.querySelectorAll('#user-dashboard .tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all user tab buttons
    document.querySelectorAll('#user-dashboard .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`user-${tabName}-tab`).classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
    
    currentUserTab = tabName;
    
    // Load notifications when notifications tab is shown
    if (tabName === 'notifications') {
        loadUserNotifications();
    }
}


function editProfile() {
    // If no user logged in, show message
    if (!isUserLoggedIn || !currentUser) {
        showToast('No user is logged in.', 'error');
        return;
    }

    // Build a simple modal form
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.display = 'flex';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    modal.style.background = 'rgba(0,0,0,0.5)';
    modal.style.zIndex = '9999';
    modal.innerHTML = `
        <div class="modal-card" style="background:#fff;padding:1.5rem;border-radius:8px;min-width:320px;max-width:520px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin-top:0;margin-bottom:1rem;">Edit Profile</h3>
            <div style="display:flex;flex-direction:column;gap:0.75rem;">
                <input id="ep_name" type="text" placeholder="Full name" value="${currentUser.name || ''}" style="padding:0.5rem;border:1px solid #ddd;border-radius:4px;"/>
                <input id="ep_email" type="email" placeholder="Email" value="${currentUser.email || ''}" style="padding:0.5rem;border:1px solid #ddd;border-radius:4px;"/>
                <input id="ep_phone" type="tel" placeholder="Contact Number" value="${currentUser.contact || ''}" style="padding:0.5rem;border:1px solid #ddd;border-radius:4px;"/>
                <select id="ep_bloodGroup" style="padding:0.5rem;border:1px solid #ddd;border-radius:4px;">
                    <option value="">Select blood group</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                </select>
            </div>
            <div style="display:flex;gap:0.5rem;margin-top:1.5rem;justify-content:flex-end;">
                <button id="ep_cancel" class="btn btn-outline" style="padding:0.5rem 1rem;">Cancel</button>
                <button id="ep_delete" class="btn btn-danger" style="padding:0.5rem 1rem;background:#dc2626;color:white;border:none;border-radius:4px;cursor:pointer;">Delete Profile</button>
                <button id="ep_save" class="btn btn-primary" style="padding:0.5rem 1rem;background:#dc2626;color:white;border:none;border-radius:4px;cursor:pointer;">Save</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Set existing blood group
    if (currentUser.blood_group) {
        const sel = document.getElementById('ep_bloodGroup');
        if (sel) sel.value = currentUser.blood_group;
    }

    // Close modal on cancel
    document.getElementById('ep_cancel').addEventListener('click', () => {
        modal.remove();
    });

    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });

    // Delete profile handler
    document.getElementById('ep_delete').addEventListener('click', async () => {
        if (!confirm('Are you sure you want to delete your profile? This action cannot be undone.')) return;
        
        try {
            if (!currentUser.id) {
                showToast('User ID not found. Cannot delete profile.', 'error');
                return;
            }

            console.log('Deleting user:', currentUser.id);
            
            const response = await fetch(`/api/users/${currentUser.id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            console.log('Delete response:', data);

            if (response.ok && data.success) {
                showToast('Profile deleted successfully', 'success');
                modal.remove();
                userLogout();
            } else {
                showToast(data.error || 'Failed to delete profile.', 'error');
            }
        } catch (err) {
            console.error('Delete profile error:', err);
            showToast('Failed to delete profile. Please try again.', 'error');
        }
    });

    // Save profile handler
    document.getElementById('ep_save').addEventListener('click', async () => {
        const name = document.getElementById('ep_name').value.trim();
        const email = document.getElementById('ep_email').value.trim();
        const contact = document.getElementById('ep_phone').value.trim();
        const blood_group = document.getElementById('ep_bloodGroup').value;

        if (!name || !email) {
            showToast('Name and email are required.', 'error');
            return;
        }

        if (!currentUser.id) {
            showToast('User ID not found. Cannot update profile.', 'error');
            return;
        }

        try {
            const requestBody = {
                name,
                email,
                contact,
                blood_group
            };
            
            console.log('Updating user:', currentUser.id, requestBody);
            
            const response = await fetch(`/api/users/${currentUser.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            console.log('Update response:', data);

            if (response.ok) {
                // Update currentUser with the response
                currentUser = { ...currentUser, ...data };
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
                showToast('Profile updated successfully', 'success');
                modal.remove();
                loadUserDashboard(); // Refresh dashboard
            } else {
                showToast(data.error || 'Failed to update profile.', 'error');
            }
        } catch (err) {
            console.error('Update profile error:', err);
            showToast('Failed to update profile. Please try again.', 'error');
        }
    });
}


function generateDonorReport(format) {
    // Show loading state
    const button = event.target;
    const originalText = button.innerHTML;
    const isPdf = format === 'pdf';
    const isExcel = format === 'excel';
    
    button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generating ${isPdf ? 'PDF' : 'Excel'} Report...`;
    button.disabled = true;
    
    // Disable both buttons during generation
    const allButtons = document.querySelectorAll('.report-options button');
    allButtons.forEach(btn => btn.disabled = true);
    
    // Determine API endpoint and file details
    const apiEndpoint = isPdf ? '/api/reports/donors' : '/api/reports/excel';
    const fileExtension = isPdf ? 'pdf' : 'xlsx';
    const reportType = isPdf ? 'Blood_Request_Report' : 'Complete_Report';
    
    // Make API call to generate report
    fetch(apiEndpoint)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to generate ${format.toUpperCase()} report`);
            }
            return response.blob();
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `LifeGrid_${reportType}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${fileExtension}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            const successMessage = isPdf 
                ? 'Blood Request PDF report generated and downloaded successfully!' 
                : 'Complete Excel report generated and downloaded successfully!';
            showToast(successMessage, 'success');
        })
        .catch(error => {
            console.error(`Error generating ${format} report:`, error);
            const errorMessage = isPdf 
                ? 'Failed to generate PDF report. Please try again.' 
                : 'Failed to generate Excel report. Please try again.';
            showToast(errorMessage, 'error');
        })
        .finally(() => {
            // Reset button states
            button.innerHTML = originalText;
            allButtons.forEach(btn => btn.disabled = false);
        });
}

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const button = input.nextElementSibling;
    const icon = button.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);


// Function to update form buttons based on login status
function updateFormButtons() {
    const donorForm = document.getElementById('donor-form');
    const requestForm = document.getElementById('request-form');
    
    if (donorForm) {
        const donorSubmitBtn = donorForm.querySelector('button[type="submit"]');
        if (donorSubmitBtn) {
            if (!isUserLoggedIn) {
                donorSubmitBtn.innerHTML = '<i class="fas fa-sign-in"></i> Please Login to Register as Donor';
                donorSubmitBtn.classList.remove('btn-primary');
                donorSubmitBtn.classList.add('btn-secondary');
                donorSubmitBtn.onclick = (e) => {
                    e.preventDefault();
                    showToast('Please login to register as a donor', 'warning');
                    showPage('login');
                };
            } else {
                donorSubmitBtn.innerHTML = '<i class="fas fa-heart"></i> Register as Donor';
                donorSubmitBtn.classList.remove('btn-secondary');
                donorSubmitBtn.classList.add('btn-primary');
                donorSubmitBtn.onclick = null;
            }
        }
    }
    
    if (requestForm) {
        const requestSubmitBtn = requestForm.querySelector('button[type="submit"]');
        if (requestSubmitBtn) {
            if (!isUserLoggedIn) {
                requestSubmitBtn.innerHTML = '<i class="fas fa-sign-in"></i> Please Login to Request Blood';
                requestSubmitBtn.classList.remove('btn-primary');
                requestSubmitBtn.classList.add('btn-secondary');
                requestSubmitBtn.onclick = (e) => {
                    e.preventDefault();
                    showToast('Please login to request blood', 'warning');
                    showPage('login');
                };
            } else {
                requestSubmitBtn.innerHTML = '<i class="fas fa-heart"></i> Submit Blood Request';
                requestSubmitBtn.classList.remove('btn-secondary');
                requestSubmitBtn.classList.add('btn-primary');
                requestSubmitBtn.onclick = null;
            }
        }
    }
}

// Notification Functions
async function loadUserNotifications() {
    if (!currentUser || !currentUser.id) {
        console.log('No user logged in');
        return;
    }

    try {
        const response = await fetch(`/api/users/${currentUser.id}/notifications`);
        const data = await response.json();
        
        if (data.notifications) {
            displayNotifications(data.notifications);
            updateNotificationBadge(data.unread_count);
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        showToast('Failed to load notifications', 'error');
    }
}

function displayNotifications(notifications) {
    const notificationsList = document.getElementById('user-notifications-list');
    
    if (!notifications || notifications.length === 0) {
        notificationsList.innerHTML = `
            <div class="notifications-empty">
                <i class="fas fa-bell-slash"></i>
                <h3>No Notifications</h3>
                <p>You don't have any notifications yet. We'll notify you when there are updates on your blood requests.</p>
            </div>
        `;
        return;
    }

    notificationsList.innerHTML = notifications.map(notification => {
        const isUnread = notification.is_read === 0;
        const typeClass = notification.type || 'info';
        const icon = getNotificationIcon(notification.type);
        const timeAgo = getTimeAgo(notification.created_at);
        
        return `
            <div class="notification-item ${isUnread ? 'unread' : ''} ${typeClass}" data-id="${notification.id}">
                <div class="notification-header">
                    <div class="notification-title">
                        <i class="${icon}"></i>
                        ${notification.title}
                    </div>
                    <div class="notification-actions">
                        ${isUnread ? `<button class="notification-btn" onclick="markNotificationRead(${notification.id})" title="Mark as read">
                            <i class="fas fa-check"></i>
                        </button>` : ''}
                        <button class="notification-btn" onclick="deleteNotification(${notification.id})" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="notification-message">${notification.message}</div>
                <div class="notification-time">
                    <i class="fas fa-clock"></i>
                    ${timeAgo}
                </div>
            </div>
        `;
    }).join('');
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'info': 'fas fa-info-circle',
        'warning': 'fas fa-exclamation-triangle'
    };
    return icons[type] || 'fas fa-bell';
}

function getTimeAgo(timestamp) {
    if (!timestamp) return 'Just now';
    
    const now = new Date();
    const notificationTime = new Date(timestamp);
    const diffInSeconds = Math.floor((now - notificationTime) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
    
    return notificationTime.toLocaleDateString();
}

function updateNotificationBadge(count) {
    // Update navbar badge
    const badgeNav = document.getElementById('notification-badge-nav');
    if (badgeNav) {
        if (count > 0) {
            badgeNav.textContent = count > 99 ? '99+' : count;
            badgeNav.style.display = 'inline-block';
        } else {
            badgeNav.style.display = 'none';
        }
    }
    
    // Show/hide notification icon in navbar
    const notifNavItem = document.getElementById('notification-nav-item');
    if (notifNavItem && isUserLoggedIn) {
        notifNavItem.style.display = 'block';
    } else if (notifNavItem) {
        notifNavItem.style.display = 'none';
    }
}

function toggleNotificationDropdown(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const dropdown = document.getElementById('notification-dropdown');
    
    if (dropdown.style.display === 'none' || dropdown.style.display === '') {
        // Open dropdown
        dropdown.style.display = 'block';
        loadNotificationDropdown();
        
        // Close dropdown when clicking outside
        setTimeout(() => {
            document.addEventListener('click', closeNotificationDropdown);
        }, 0);
    } else {
        // Close dropdown
        dropdown.style.display = 'none';
        document.removeEventListener('click', closeNotificationDropdown);
    }
}

function closeNotificationDropdown(event) {
    const dropdown = document.getElementById('notification-dropdown');
    const notifItem = document.getElementById('notification-nav-item');
    
    if (dropdown && !notifItem.contains(event.target)) {
        dropdown.style.display = 'none';
        document.removeEventListener('click', closeNotificationDropdown);
    }
}

async function loadNotificationDropdown() {
    if (!currentUser || !currentUser.id) return;
    
    try {
        const response = await fetch(`/api/users/${currentUser.id}/notifications`);
        const data = await response.json();
        
        if (data.notifications) {
            displayNotificationDropdown(data.notifications);
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

function displayNotificationDropdown(notifications) {
    const dropdownList = document.getElementById('notification-dropdown-list');
    
    if (!notifications || notifications.length === 0) {
        dropdownList.innerHTML = `
            <div class="notification-dropdown-empty">
                <i class="fas fa-bell-slash"></i>
                <p>No notifications yet</p>
            </div>
        `;
        return;
    }
    
    // Show all notifications in dropdown with scrollbar
    dropdownList.innerHTML = notifications.map(notification => {
        const isUnread = notification.is_read === 0;
        const icon = getNotificationIcon(notification.type);
        const timeAgo = getTimeAgo(notification.created_at);
        
        return `
            <div class="notification-dropdown-item ${isUnread ? 'unread' : ''}" 
                 onclick="handleNotificationClick(${notification.id})">
                <div class="notification-dropdown-icon ${notification.type}">
                    <i class="${icon}"></i>
                </div>
                <div class="notification-dropdown-content">
                    <div class="notification-dropdown-title">
                        ${notification.title}
                        ${isUnread ? '<span class="unread-indicator"></span>' : ''}
                    </div>
                    <div class="notification-dropdown-message">${notification.message}</div>
                    <div class="notification-dropdown-time">
                        <i class="fas fa-clock"></i> ${timeAgo}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function handleNotificationClick(notificationId) {
    // Mark as read
    await markNotificationRead(notificationId);
    
    // Close dropdown
    const dropdown = document.getElementById('notification-dropdown');
    if (dropdown) {
        dropdown.style.display = 'none';
    }
    
    // Reload dropdown to update read status
    await loadNotificationDropdown();
}

async function markNotificationRead(notificationId) {
    if (!currentUser || !currentUser.id) return;

    try {
        const response = await fetch(`/api/users/${currentUser.id}/notifications/${notificationId}/read`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // Reload notifications to update UI
            await loadUserNotifications();
            showToast('Notification marked as read', 'success');
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
        showToast('Failed to mark notification as read', 'error');
    }
}

async function markAllNotificationsRead() {
    if (!currentUser || !currentUser.id) return;

    try {
        const response = await fetch(`/api/users/${currentUser.id}/notifications/read-all`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // Reload notifications to update UI
            await loadUserNotifications();
            
            // Refresh dropdown if it's open
            const dropdown = document.getElementById('notification-dropdown');
            if (dropdown && dropdown.style.display === 'block') {
                await loadNotificationDropdown();
            }
            
            showToast('All notifications marked as read', 'success');
        }
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        showToast('Failed to mark notifications as read', 'error');
    }
}

async function deleteNotification(notificationId) {
    if (!currentUser || !currentUser.id) return;

    if (!confirm('Are you sure you want to delete this notification?')) {
        return;
    }

    try {
        const response = await fetch(`/api/users/${currentUser.id}/notifications/${notificationId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // Reload notifications to update UI
            await loadUserNotifications();
            showToast('Notification deleted', 'success');
        }
    } catch (error) {
        console.error('Error deleting notification:', error);
        showToast('Failed to delete notification', 'error');
    }
}
