/* JavaScript code */
// Get a reference to the button and form
const button = document.getElementById("book-appointment-button");
const form = document.getElementById("contact-form");

// Add a click event listener to the button
button.addEventListener("click", () => {
  // Display an alert when the button is clicked
  alert("Booking an appointment is not yet available. Please contact us for more information.");
});

// Add a submit event listener to the form
form.addEventListener("submit", (event) => {
  // Prevent the form from being submitted
  event.preventDefault();

  // Get the user's name and email address
  const name = document.getElementById("name").value;
  const email = document.getElementById("email").value;

  // Display a message to the user
  alert(`Thank you for your message, ${name} (${email}). We will get back to you as soon as possible.`);
});
