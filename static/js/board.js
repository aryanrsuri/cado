document.addEventListener('DOMContentLoaded', function() {
    const issueCards = document.querySelectorAll('.issue-card');
    
    issueCards.forEach(card => {
        card.draggable = true;
        
        card.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('text/plain', this.dataset.issueId);
            this.style.opacity = '0.5';
        });
        
        card.addEventListener('dragend', function() {
            this.style.opacity = '1';
        });
    });
    
    const columnContainers = document.querySelectorAll('.column-container');
    
    columnContainers.forEach(container => {
        const columnId = container.dataset.columnId;
        
        container.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.backgroundColor = '#f0f0f0';
        });
        
        container.addEventListener('dragleave', function() {
            this.style.backgroundColor = '#f3f3f3';
        });
        
        container.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.backgroundColor = '#f3f3f3';
            
            const issueId = e.dataTransfer.getData('text/plain');
            const moveForm = document.createElement('form');
            moveForm.method = 'POST';
            moveForm.action = `/issue/${issueId}/move`;
            
            const columnIdInput = document.createElement('input');
            columnIdInput.type = 'hidden';
            columnIdInput.name = 'column_id';
            columnIdInput.value = columnId;
            
            const positionInput = document.createElement('input');
            positionInput.type = 'hidden';
            positionInput.name = 'position';
            positionInput.value = '0';
            
            moveForm.appendChild(columnIdInput);
            moveForm.appendChild(positionInput);
            document.body.appendChild(moveForm);
            moveForm.submit();
        });
    });
});

