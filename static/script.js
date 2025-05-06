function fetchSlots() {
    const barberId = document.getElementById('barber_id').value;
    const date = document.getElementById('date').value;
    const timeSelect = document.getElementById('time');

    // Clear previous options
    timeSelect.innerHTML = '<option value="">Choose a time</option>';

    if (barberId && date) {
        fetch(`/slots?barber_id=${barberId}&date=${date}`)
            .then(response => response.json())
            .then(data => {
                if (data.slots) {
                    data.slots.forEach(slot => {
                        const option = document.createElement('option');
                        option.value = slot;
                        option.textContent = slot;
                        timeSelect.appendChild(option);
                    });
                } else {
                    alert('No slots available or invalid request.');
                }
            })
            .catch(error => {
                console.error('Error fetching slots:', error);
                alert('Failed to load time slots.');
            });
    }
}