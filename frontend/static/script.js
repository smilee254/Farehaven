// App State
let busPulseActive = true;

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
    fetchQuote();
    checkBusPulseStatus();
    fetchTermProgress();
    setupInteractiveRose();

    // Hamburger Menu
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('show');
        });
    }
});

// Section Navigation
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.remove('active');
        sec.classList.add('hidden');
    });

    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }

    // Close mobile menu if open
    const navLinks = document.querySelector('.nav-links');
    if (navLinks && navLinks.classList.contains('show')) {
        navLinks.classList.remove('show');
    }

    // Refresh data if needed based on section
    if (sectionId === 'transport') {
        checkBusPulseStatus();
    }
}

// Interactive Rose Background
function setupInteractiveRose() {
    const roseBg = document.getElementById('roseBg');
    if (!roseBg) return;

    window.addEventListener('mousemove', (e) => {
        const x = (e.clientX / window.innerWidth - 0.5) * 20; // -10 to 10
        const y = (e.clientY / window.innerHeight - 0.5) * 20;

        // Gentle translation based on mouse
        roseBg.style.transform = `translate(${x}px, ${y}px)`;
    });
}

// API Calls
async function fetchQuote() {
    try {
        const res = await fetch('/api/quote');
        const data = await res.json();
        document.getElementById('weeklyQuote').innerText = data.quote;
    } catch (e) {
        document.getElementById('weeklyQuote').innerText = "Empowering journeys, enriching lives.";
        console.error("Error fetching quote:", e);
    }
}

async function checkBusPulseStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        busPulseActive = data.bus_pulse_active;
        updatePulseUI();
    } catch (e) {
        console.error("Error fetching bus status:", e);
    }
}

async function fetchTermProgress() {
    try {
        const res = await fetch('/api/term_progress');
        const data = await res.json();

        document.getElementById('termName').innerText = data.term;
        document.getElementById('termProgressFill').style.width = `${data.progress_percent}%`;
        document.getElementById('termProgressText').innerText = `${data.progress_percent}% Complete (Week ${data.weeks_elapsed} of ${data.total_weeks})`;
    } catch (e) {
        console.error("Error fetching term progress:", e);
    }
}

// UI Updates
function updatePulseUI() {
    const statusSpan = document.getElementById('busPulseStatus');
    const adminToggle = document.getElementById('adminPulseToggle');
    const adminLabel = document.getElementById('adminPulseLabel');
    const busIcon = document.getElementById('busIcon');

    if (statusSpan) {
        statusSpan.innerText = busPulseActive ? 'Active' : 'Inactive';
        statusSpan.className = `status-badge ${busPulseActive ? 'active' : 'inactive'}`;
    }

    if (adminToggle) {
        adminToggle.checked = busPulseActive;
    }

    if (adminLabel) {
        adminLabel.innerText = busPulseActive ? 'Active' : 'Inactive';
    }

    if (busIcon) {
        if (busPulseActive) {
            busIcon.style.animationPlayState = 'running';
            busIcon.style.color = 'var(--success)';
        } else {
            busIcon.style.animationPlayState = 'paused';
            busIcon.style.color = 'var(--danger)';
        }
    }
}

// Forms
function toggleChamaDetails() {
    const isChama = document.getElementById('chamaToggle').checked;
    const detailsContainer = document.getElementById('chamaDetails');
    if (isChama) {
        detailsContainer.classList.add('expanded');
    } else {
        detailsContainer.classList.remove('expanded');
    }
}

async function submitForm(e, type) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    data.type = type;

    // Convert checkbox to boolean
    if (type === 'event') {
        data.is_chama = document.getElementById('chamaToggle').checked;
    }

    try {
        const res = await fetch('/api/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await res.json();
        if (result.success) {
            alert(`Booking successful! Your ID is: ${result.booking_id}`);
            e.target.reset();
            if (type === 'event') toggleChamaDetails(); // reset UI
        }
    } catch (err) {
        alert("An error occurred during booking. Please try again.");
        console.error(err);
    }
}

// Admin Actions
async function togglePulseStatus() {
    const isChecked = document.getElementById('adminPulseToggle').checked;
    try {
        const res = await fetch('/api/status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bus_pulse_active: isChecked })
        });
        const data = await res.json();
        if (data.success) {
            busPulseActive = data.bus_pulse_active;
            updatePulseUI();
        }
    } catch (e) {
        console.error("Error updating bus status:", e);
        // revert toggle on error
        document.getElementById('adminPulseToggle').checked = !isChecked;
    }
}

function exportData() {
    window.location.href = '/api/export';
}
