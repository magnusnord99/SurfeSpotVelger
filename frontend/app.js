// Frontend JavaScript for SurfeSpotVelger
let selectedRating = 0;
let spots = [];

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadSpots();
    loadSessions();
    setupEventListeners();
    setDefaultDateTime();
});

function setupEventListeners() {
    // Rating buttons
    document.querySelectorAll('.rating-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            selectRating(parseInt(this.dataset.rating));
        });
    });
    
    // Form submission
    document.getElementById('sessionForm').addEventListener('submit', handleSubmit);
}

function setDefaultDateTime() {
    // Set default to current time
    const now = new Date();
    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    document.getElementById('datetime').value = localDateTime.toISOString().slice(0, 16);
}

function selectRating(rating) {
    selectedRating = rating;
    
    // Update button styles
    document.querySelectorAll('.rating-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    document.querySelector(`[data-rating="${rating}"]`).classList.add('selected');
    
    // Update rating text
    const ratingTexts = {
        1: 'Dårlig 😞',
        2: 'Ok 😐', 
        3: 'Bra 🙂',
        4: 'Veldig bra 😊',
        5: 'Episk! 🤩'
    };
    document.getElementById('rating-text').textContent = ratingTexts[rating];
}

async function loadSpots() {
    try {
        const response = await fetch('/api/spots');
        spots = await response.json();
        
        const spotSelect = document.getElementById('spot');
        spotSelect.innerHTML = '<option value="">Velg spot...</option>';
        
        spots.forEach(spot => {
            const option = document.createElement('option');
            option.value = spot.id;
            option.textContent = spot.name;
            spotSelect.appendChild(option);
        });
    } catch (error) {
        showMessage('Feil ved lasting av spots', 'error');
        console.error('Error loading spots:', error);
    }
}

async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const sessions = await response.json();
        
        displaySessions(sessions);
    } catch (error) {
        document.getElementById('sessionsList').innerHTML = 
            '<div class="error">Feil ved lasting av økter</div>';
        console.error('Error loading sessions:', error);
    }
}

function displaySessions(sessions) {
    const sessionsList = document.getElementById('sessionsList');
    
    if (sessions.length === 0) {
        sessionsList.innerHTML = '<p>Ingen økter registrert ennå.</p>';
        return;
    }
    
    sessionsList.innerHTML = sessions.map(session => {
        const spot = spots.find(s => s.id === session.spot_id);
        const spotName = spot ? spot.name : 'Ukjent spot';
        const date = new Date(session.date_time).toLocaleString('no-NO');
        
        // Weather info
        let weatherInfo = '';
        if (session.wave_height || session.wind_speed) {
            weatherInfo = `
                <div class="weather-info">
                    ${session.wave_height ? `<div>Bølger: ${session.wave_height.toFixed(1)}m</div>` : ''}
                    ${session.wind_speed ? `<div>Vind: ${session.wind_speed.toFixed(1)} m/s</div>` : ''}
                    ${session.wind_direction ? `<div>Vindretning: ${session.wind_direction}°</div>` : ''}
                    ${session.offshore_wind !== null ? `<div>${session.offshore_wind ? 'Offshore' : 'Onshore'}</div>` : ''}
                </div>
            `;
        }
        
        return `
            <div class="session-item">
                <div class="session-header">
                    <div>
                        <div class="session-spot">${spotName}</div>
                        <div class="session-date">${date}</div>
                    </div>
                    <div class="session-rating">${session.rating}/5</div>
                </div>
                ${session.notes ? `<p><strong>Notater:</strong> ${session.notes}</p>` : ''}
                ${weatherInfo}
            </div>
        `;
    }).join('');
}

async function handleSubmit(event) {
    event.preventDefault();
    
    if (selectedRating === 0) {
        showMessage('Vennligst velg en rating', 'error');
        return;
    }
    
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Lagrer... (henter værdata)';
    
    const formData = {
        spot_id: parseInt(document.getElementById('spot').value),
        date_time: document.getElementById('datetime').value,
        duration_minutes: document.getElementById('duration').value ? 
            parseInt(document.getElementById('duration').value) : null,
        rating: selectedRating,
        board_type: document.getElementById('board').value || null,
        notes: document.getElementById('notes').value || null
    };
    
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showMessage('Surf-økt lagret! Værdata hentet automatisk.', 'success');
            resetForm();
            loadSessions(); // Refresh sessions list
        } else {
            const error = await response.json();
            showMessage(`Feil: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage('Feil ved lagring av økt', 'error');
        console.error('Error saving session:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Logg surf-økt';
    }
}

function resetForm() {
    document.getElementById('sessionForm').reset();
    selectedRating = 0;
    document.querySelectorAll('.rating-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    document.getElementById('rating-text').textContent = 'Velg rating';
    setDefaultDateTime();
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = `<div class="${type}">${message}</div>`;
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageDiv.innerHTML = '';
    }, 5000);
}
