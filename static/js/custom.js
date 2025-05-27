// Custom JavaScript for SkillTrain App
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Initialize date pickers
    var dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        if (!input.value) {
            input.value = new Date().toISOString().split('T')[0];
        }
    });

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Dynamic task status updates
    var statusButtons = document.querySelectorAll('.task-status-btn');
    statusButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var taskId = this.dataset.taskId;
            var newStatus = this.dataset.status;
            
            fetch('/update_task_status/' + taskId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    status: newStatus
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error updating task status');
                }
            });
        });
    });

    // Program enrollment handling
    var enrollButtons = document.querySelectorAll('.enroll-btn');
    enrollButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var programId = this.dataset.programId;
            
            fetch('/enroll_program/' + programId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.message || 'Error enrolling in program');
                }
            });
        });
    });
}); 