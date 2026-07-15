
// Initialize AOS
document.addEventListener('DOMContentLoaded', function () {
    AOS.init({
        once: true,
        offset: 50,
        duration: 800,
    });
});

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.innerText = message;
    toast.className = "show";
    setTimeout(function () { toast.className = toast.className.replace("show", ""); }, 3000);
}

function scrollToSection(id) {
    const element = document.getElementById(id);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

// Modal Logic
function toggleModal() {
    const modal = document.querySelector('.modal');
    // const body = document.querySelector('body');

    if (modal.classList.contains('opacity-0')) {
        modal.classList.remove('opacity-0', 'pointer-events-none');
        // body.classList.toggle('modal-active');
    } else {
        modal.classList.add('opacity-0', 'pointer-events-none');
        // body.classList.toggle('modal-active');
    }
}

// Close modal when clicking outside
document.querySelectorAll('.modal-overlay').forEach(function (el) {
    el.addEventListener('click', toggleModal);
});

// Reuse handleContact for modal form
async function handleContact(isModal = false) {
    let name, email, message;

    if (isModal) {
        name = document.getElementById('modal-name').value;
        email = document.getElementById('modal-email').value;
        const interest = document.getElementById('modal-interest').value;
        message = `Application for ${interest} (from Modal)`;
    } else {
        name = document.getElementById('contact-name').value;
        email = document.getElementById('contact-email').value;
        message = document.getElementById('contact-message').value;
    }

    if (!name || !email || !message) {
        showToast("Please fill in all fields.");
        return;
    }

    try {
        const response = await fetch('/api/contact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name, email: email, message: message }),
        });
        const result = await response.json();
        if (result.status === 'success') {
            showToast(result.message);

            // Clear fields
            if (isModal) {
                document.getElementById('modal-name').value = '';
                document.getElementById('modal-email').value = '';
                toggleModal(); // Close modal on success
            } else {
                document.getElementById('contact-name').value = '';
                document.getElementById('contact-email').value = '';
                document.getElementById('contact-message').value = '';
            }
        } else {
            showToast("Error: " + result.message);
        }
    } catch (error) {
        showToast("An error occurred. Please try again.");
        console.error('Error:', error);
    }
}


function handleProgramClick(programName) {
    // Open modal and pre-select interest if matched, otherwise just show modal
    const modal = document.querySelector('.modal');
    const select = document.getElementById('modal-interest');

    if (select) {
        for (let i = 0; i < select.options.length; i++) {
            if (select.options[i].text.includes(programName)) {
                select.selectedIndex = i;
                break;
            }
        }
    }

    toggleModal();
}



async function handleFeedback() {
    const email = document.getElementById('feedback-email').value;
    const message = document.getElementById('feedback-message').value;

    if (!email || !message) {
        showToast("Please fill in all fields.");
        return;
    }

    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email, feedback: message }),
        });
        const result = await response.json();
        if (result.status === 'success') {
            showToast(result.message);
            document.getElementById('feedback-email').value = '';
            document.getElementById('feedback-message').value = '';
        } else {
            showToast("Error: " + result.message);
        }
    } catch (error) {
        showToast("An error occurred. Please try again.");
        console.error('Error:', error);
    }
}

function toggleMobileMenu() {
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenu) {
        mobileMenu.classList.toggle('hidden');
    }
}
