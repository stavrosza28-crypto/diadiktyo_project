// Η διεύθυνση του backend μας
const API_BASE_URL = 'http://localhost:3000/movielens/api';

// Εδώ θα αποθηκεύονται οι αξιολογήσεις  κατά τη διάρκεια του session

let sessionRatings = []; 


// 1. Προσθήκη Νέας Ταινίας 

document.getElementById('add-movie-btn').addEventListener('click', async () => {
    const title = document.getElementById('new-movie-title').value;
    const genres = document.getElementById('new-movie-genres').value;
    const messageEl = document.getElementById('add-movie-message');

    // Απλός έλεγχος για άδεια πεδία
    if (!title || !genres) {
        messageEl.textContent = 'Παρακαλώ συμπληρώστε και τα δύο πεδία.';
        messageEl.style.color = 'red';
        return;
    }

    try {
        // Στέλνουμε POST request στο 3ο API 
        const response = await fetch(`${API_BASE_URL}/movies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title, genres: genres })
        });
        const data = await response.json();

        if (data.status === 'success') {
            messageEl.textContent = `Επιτυχία! Το νέο ID της ταινίας είναι: ${data.movieId}`;
            messageEl.style.color = 'green';
            // Καθαρισμός των πεδίων [cite: 106]
            document.getElementById('new-movie-title').value = '';
            document.getElementById('new-movie-genres').value = '';
        }
    } catch (error) {
        messageEl.textContent = 'Σφάλμα κατά την προσθήκη της ταινίας.';
        messageEl.style.color = 'red';
    }
});


// 2. Αναζήτηση Ταινιών

document.getElementById('search-btn').addEventListener('click', async () => {
    const keyword = document.getElementById('search-keyword').value;
    const resultsDiv = document.getElementById('search-results');
    resultsDiv.innerHTML = '<p>Αναζήτηση...</p>'; // Gενικό μήνυμα αναζήτησης GET 

    try {
        // Καλούμε το 1ο API 
        const response = await fetch(`${API_BASE_URL}/movies?search=${encodeURIComponent(keyword)}`);
        const data = await response.json();

        if (data.status === 'success') {
            displaySearchResults(data.movies);
        }
    } catch (error) {
        resultsDiv.innerHTML = '<p>Σφάλμα κατά την αναζήτηση.</p>';
    }
});

function displaySearchResults(movies) {
    const resultsDiv = document.getElementById('search-results');
    resultsDiv.innerHTML = ''; 

    if (movies.length === 0) {
        resultsDiv.innerHTML = '<p>Δεν βρέθηκαν ταινίες.</p>';
        return;
    }

    // Περιορίζουμε στα 20 πρώτα αποτελέσματα για να μην γεμίσει υπερβολικά η οθόνη
    movies.slice(0, 20).forEach(movie => {
        const movieDiv = document.createElement('div');
        movieDiv.style.border = "1px solid #ccc";
        movieDiv.style.padding = "10px";
        movieDiv.style.marginBottom = "10px";
        
        movieDiv.innerHTML = `
            <h3>${movie.title} <small>(${movie.genres})</small></h3>
            <div>
                <input type="number" id="rating-${movie.movieId}" min="0.5" max="5" step="0.5" placeholder="Βαθμολογία (0.5 - 5)">
                <button onclick="rateMovie(${movie.movieId})">Αξιολόγηση</button>
                <button onclick="showAverage(${movie.movieId})">Μέσος Όρος</button>
            </div>
            <p id="avg-rating-${movie.movieId}" style="color: blue; font-weight: bold;"></p>
        `;
        resultsDiv.appendChild(movieDiv);
    });
}


// 3. Αξιολόγηση και Μέσος Όρος 

// Η λειτουργία rateMovie απλά σώζει τη βαθμολογία στη μνήμη
window.rateMovie = function(movieId) {
    const ratingInput = document.getElementById(`rating-${movieId}`).value;
    const rating = parseFloat(ratingInput);

    if (isNaN(rating) || rating < 0.5 || rating > 5) {
        alert('Παρακαλώ εισάγετε μια βαθμολογία από 0.5 έως 5.');
        return;
    }

    // Αν ο χρήστης έχει ξαναβαθμολογήσει την ταινία, ανανεώνουμε τη βαθμολογία του
    const existingIndex = sessionRatings.findIndex(r => r.movieId === movieId);
    if (existingIndex > -1) {
        sessionRatings[existingIndex].rating = rating;
    } else {
        sessionRatings.push({ movieId: movieId, rating: rating });
    }
    
    alert(`Η αξιολόγηση (${rating}) αποθηκεύτηκε στη μνήμη!`);
};

// Η λειτουργία showAverage καλεί το 2ο API μας
window.showAverage = async function(movieId) {
    const avgDiv = document.getElementById(`avg-rating-${movieId}`);
    avgDiv.textContent = 'Υπολογισμός...';

    try {
        const response = await fetch(`${API_BASE_URL}/ratings/${movieId}`);
        const data = await response.json();

        if (data.status === 'success' && data.ratings.length > 0) {
            // Υπολογισμός του μέσου όρου
            const sum = data.ratings.reduce((acc, curr) => acc + curr.rating, 0);
            const avg = (sum / data.ratings.length).toFixed(2);
            avgDiv.textContent = `Μέση βαθμολογία: ${avg} (από ${data.ratings.length} αξιολογήσεις)`;
        } else {
            avgDiv.textContent = 'Δεν υπάρχουν βαθμολογίες για αυτή την ταινία.';
        }
    } catch (error) {
        avgDiv.textContent = 'Σφάλμα.';
    }
};

// 4. Λήψη Συστάσεων 

document.getElementById('get-recommendations-btn').addEventListener('click', async () => {
    const resultsDiv = document.getElementById('recommendations-results');
    
    // Έλεγχος αν ο χρήστης έχει δώσει έστω και μία βαθμολογία
    if (sessionRatings.length === 0) {
        resultsDiv.innerHTML = '<p style="color:red;">Πρέπει να βαθμολογήσετε τουλάχιστον μία ταινία πρώτα!</p>';
        return;
    }

    resultsDiv.innerHTML = '<p>Υπολογισμός συστάσεων... Παρακαλώ περιμένετε (μπορεί να διαρκέσει μερικά δευτερόλεπτα).</p>';

    try {
        // Στέλνουμε τις βαθμολογίες της μνήμης στο 4ο API [cite: 92]
        const response = await fetch(`${API_BASE_URL}/recommendations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ratings: sessionRatings })
        });
        const data = await response.json();

        if (data.status === 'success') {
            displayRecommendations(data.recommendations);
        }
    } catch (error) {
        resultsDiv.innerHTML = '<p style="color:red;">Σφάλμα κατά τη λήψη συστάσεων.</p>';
    }
});

function displayRecommendations(recs) {
    const resultsDiv = document.getElementById('recommendations-results');
    resultsDiv.innerHTML = '';

    if (recs.length === 0) {
        resultsDiv.innerHTML = '<p>Δεν βρέθηκαν συστάσεις με βάση τις επιλογές σας.</p>';
        return;
    }

    // Εμφάνιση των συστάσεων σε λίστα
    const ul = document.createElement('ul');
    recs.forEach(rec => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${rec.title}</strong> (${rec.genres}) - Πρόβλεψη: <span style="color: green; font-weight: bold;">${rec.predictedRating}/5</span>`;
        ul.appendChild(li);
    });
    resultsDiv.appendChild(ul);
}
document.getElementById('tag-search-btn').addEventListener('click', async () => {
    const keyword = document.getElementById('tag-search-keyword').value;
    const resultsDiv = document.getElementById('tag-search-results');
    resultsDiv.innerHTML = '<p>Αναζήτηση με βάση tag...</p>';

    try {
        // Υποχρεωτικό POST request
        const response = await fetch(`${API_BASE_URL}/tags/movies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ search: keyword })
        });
        const data = await response.json();

        if (data.status === 'success') {
            displayTagSearchResults(data.movies);
        }
    } catch (error) {
        resultsDiv.innerHTML = '<p style="color:red;">Σφάλμα κατά την αναζήτηση tag.</p>';
    }
});

function displayTagSearchResults(movies) {
    const resultsDiv = document.getElementById('tag-search-results');
    resultsDiv.innerHTML = ''; 

    if (movies.length === 0) {
        resultsDiv.innerHTML = '<p>Δεν βρέθηκαν ταινίες για αυτή την ετικέτα.</p>';
        return;
    }

    // Εμφάνιση των αποτελεσμάτων σε Πίνακα (Table) 
    let tableHTML = `
        <table border="1" style="width: 100%; border-collapse: collapse; margin-top: 15px; text-align: left;">
            <thead>
                <tr style="background-color: #3498db; color: white;">
                    <th style="padding: 10px;">ID</th>
                    <th style="padding: 10px;">Τίτλος</th>
                    <th style="padding: 10px;">Είδη</th>
                    <th style="padding: 10px;">Tag που ταίριαξε</th>
                </tr>
            </thead>
            <tbody>
    `;

    movies.forEach(movie => {
        tableHTML += `
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${movie.movieId}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>${movie.title}</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${movie.genres}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; color: green; font-weight: bold;">${movie.matchingTag}</td>
            </tr>
        `;
    });

    tableHTML += `
            </tbody>
        </table>
    `;
    
    resultsDiv.innerHTML = tableHTML;
}
// ----------
