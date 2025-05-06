document.addEventListener('DOMContentLoaded', () => {
    const barberSelect = document.getElementById('barber');
    const dateInput = document.getElementById('date');
    const timeSelect = document.getElementById('time');

    function updateTimes() {
        const barberId = barberSelect.value;
        const date = dateInput.value;
        if (barberId && date) {
            fetch(`/slots?barber_id=${barberId}&date=${date}`)
                .then(response => response.json())
                .then(slots => {
                    timeSelect.innerHTML = '<option value="">Select a time</option>';
                    slots.forEach(slot => {
                        const option = document.createElement('option');
                        option.value = slot;
                        option.textContent = slot;
                        timeSelect.appendChild(option);
                    });
                })
                .catch(error => console.error('Error fetching slots:', error));
        }
    }

    barberSelect.addEventListener('change', updateTimes);
    dateInput.addEventListener('change', updateTimes);
});