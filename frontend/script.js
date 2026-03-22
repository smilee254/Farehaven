document.addEventListener('DOMContentLoaded', () => {
    const inputs = document.querySelectorAll('input, select');
    const roseContainer = document.getElementById('rose-container');

    // Interactive rose scaling on input focus
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            roseContainer.classList.add('interactive-scale');
        });

        input.addEventListener('blur', () => {
            // Slight delay to check if another input is clicked/focused
            setTimeout(() => {
                const anyFocused = Array.from(inputs).some(el => el === document.activeElement);
                if (!anyFocused) {
                    roseContainer.classList.remove('interactive-scale');
                }
            }, 50);
        });
    });

    const form = document.getElementById('registrationForm');
    const formMessage = document.getElementById('formMessage');
    const submitBtn = document.getElementById('submitBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Gather data
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        const ogText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span>Registering...</span>';
        submitBtn.disabled = true;
        formMessage.style.display = 'none';

        try {
            // Note: Update this endpoint if hosted differently
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                // Success
                formMessage.className = 'form-message success';
                formMessage.textContent = 'Registration successful! We will contact you soon.';
                formMessage.style.display = 'block';
                form.reset();
                roseContainer.classList.remove('interactive-scale');
            } else {
                // Server error
                formMessage.className = 'form-message error';
                formMessage.textContent = 'Registration failed. Please try again later.';
                formMessage.style.display = 'block';
            }
        } catch (err) {
            // Network error
            formMessage.className = 'form-message error';
            formMessage.textContent = 'Network error. Please try again.';
            formMessage.style.display = 'block';
        } finally {
            submitBtn.innerHTML = ogText;
            submitBtn.disabled = false;
        }
    });
});
