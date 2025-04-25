document.addEventListener('DOMContentLoaded', function() {
    // Get elements
    const wbsQueryForm = document.getElementById('wbs-query-form');
    const queryResultsDiv = document.getElementById('query-results');
    const resultsContainer = document.getElementById('results-container');
    const toggleWbsTreeBtn = document.getElementById('toggle-wbs-tree');
    const wbsTreeContainer = document.getElementById('wbs-tree-container');
    const wbsTreeBody = document.getElementById('wbs-tree-body');
    const wbsItemsContainer = document.getElementById('wbs-items-container');
    
    // Track next item ID for dynamic items
    let nextItemId = 2; // Start from 2 since we already have item 1
    
    // Load full WBS data for reference
    fetchFullWbs();
    
    // Set up event delegation for the form
    setupEventDelegation();
    
    // Handle "Add Item" button clicks - using event delegation
    function setupEventDelegation() {
        // Add event delegation for handling level1 select changes
        wbsItemsContainer.addEventListener('change', function(e) {
            // Check if the changed element is a level1 select
            if (e.target.classList.contains('level1-select')) {
                handleLevel1Change(e.target);
            }
            // Check if the changed element is a level2 select
            else if (e.target.classList.contains('level2-select')) {
                handleLevel2Change(e.target);
            }
        });
        
        // Add event delegation for add item buttons
        wbsItemsContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('add-item-btn') || 
                e.target.parentElement.classList.contains('add-item-btn')) {
                // Find the actual button element (could be the icon or the button)
                const button = e.target.classList.contains('add-item-btn') ? 
                               e.target : e.target.parentElement;
                
                // Add a new WBS item
                addNewWbsItem();
                
                // Prevent form submission
                e.preventDefault();
            }
        });
    }
    
    // Handle level1 select change
    function handleLevel1Change(level1Select) {
        const itemId = getItemIdFromElement(level1Select);
        const level2Select = document.getElementById(`level2-${itemId}`);
        const level3Select = document.getElementById(`level3-${itemId}`);
        
        // Clear and disable level 3 dropdown
        level3Select.innerHTML = '<option value="" class="dropdown-placeholder">請先選擇第二階層</option>';
        level3Select.disabled = true;
        
        const selectedLevel1 = level1Select.value;
        
        if (selectedLevel1) {
            // Fetch level 2 options based on level 1 selection
            const formData = new FormData();
            formData.append('parent_level', 'level1');
            formData.append('parent_value', selectedLevel1);
            
            fetch('/get_options', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Populate level 2 dropdown with options
                level2Select.innerHTML = '<option value="" class="dropdown-placeholder">請選擇第二階層項目</option>';
                
                // Add options from the response
                Object.keys(data).forEach(option => {
                    const optionElement = document.createElement('option');
                    optionElement.value = option;
                    optionElement.textContent = option;
                    level2Select.appendChild(optionElement);
                });
                
                // Enable level 2 dropdown
                level2Select.disabled = false;
            })
            .catch(error => {
                console.error('Error fetching level 2 options:', error);
                level2Select.innerHTML = '<option value="" class="dropdown-placeholder">載入選項時發生錯誤</option>';
            });
        } else {
            // Reset level 2 dropdown if no level 1 is selected
            level2Select.innerHTML = '<option value="" class="dropdown-placeholder">請先選擇第一階層</option>';
            level2Select.disabled = true;
        }
    }
    
    // Handle level2 select change
    function handleLevel2Change(level2Select) {
        const itemId = getItemIdFromElement(level2Select);
        const level1Select = document.getElementById(`level1-${itemId}`);
        const level3Select = document.getElementById(`level3-${itemId}`);
        
        const selectedLevel1 = level1Select.value;
        const selectedLevel2 = level2Select.value;
        
        if (selectedLevel1 && selectedLevel2) {
            // Fetch level 3 options based on level 1 and level 2 selections
            const formData = new FormData();
            formData.append('parent_level', 'level2');
            formData.append('parent_value', selectedLevel2);
            formData.append('level1_value', selectedLevel1);
            
            fetch('/get_options', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Populate level 3 dropdown with options
                level3Select.innerHTML = '<option value="" class="dropdown-placeholder">請選擇第三階層項目</option>';
                
                // Add options from the response
                data.forEach(option => {
                    const optionElement = document.createElement('option');
                    optionElement.value = option;
                    optionElement.textContent = option;
                    level3Select.appendChild(optionElement);
                });
                
                // Enable level 3 dropdown if options exist
                level3Select.disabled = data.length === 0;
                
                // If no options, show a message
                if (data.length === 0) {
                    level3Select.innerHTML = '<option value="" class="dropdown-placeholder">無第三階層項目</option>';
                }
            })
            .catch(error => {
                console.error('Error fetching level 3 options:', error);
                level3Select.innerHTML = '<option value="" class="dropdown-placeholder">載入選項時發生錯誤</option>';
            });
        } else {
            // Reset level 3 dropdown if no level 2 is selected
            level3Select.innerHTML = '<option value="" class="dropdown-placeholder">請先選擇第二階層</option>';
            level3Select.disabled = true;
        }
    }
    
    // Function to extract item ID from an element
    function getItemIdFromElement(element) {
        const idParts = element.id.split('-');
        return idParts[idParts.length - 1];
    }
    
    // Function to add a new WBS item
    function addNewWbsItem() {
        const itemId = nextItemId++;
        const newItem = document.createElement('div');
        newItem.className = 'wbs-item mb-4';
        newItem.dataset.itemId = itemId;
        
        // Create item content with unique IDs for selects
        newItem.innerHTML = `
            <div class="card border-light">
                <div class="card-header d-flex justify-content-between align-items-center bg-dark-subtle">
                    <h6 class="mb-0">WBS 項目 <span class="item-number">${itemId}</span></h6>
                    <div>
                        <button type="button" class="btn btn-sm btn-outline-primary add-item-btn">
                            <i class="bi bi-plus-circle"></i> 新增項目
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label for="level1-${itemId}" class="form-label">第一階層</label>
                            <select class="form-select level1-select" id="level1-${itemId}" name="items[${itemId}][level1]">
                                <option value="" class="dropdown-placeholder">請選擇工程類別</option>
                                ${getLevel1Options()}
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label for="level2-${itemId}" class="form-label">第二階層</label>
                            <select class="form-select level2-select" id="level2-${itemId}" name="items[${itemId}][level2]" disabled>
                                <option value="" class="dropdown-placeholder">請先選擇第一階層</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label for="level3-${itemId}" class="form-label">第三階層</label>
                            <select class="form-select level3-select" id="level3-${itemId}" name="items[${itemId}][level3]" disabled>
                                <option value="" class="dropdown-placeholder">請先選擇第二階層</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Append new item to container
        wbsItemsContainer.appendChild(newItem);
    }
    
    // Helper function to get level 1 options HTML
    function getLevel1Options() {
        // Clone options from the first level1 select
        const firstSelect = document.querySelector('.level1-select');
        const options = Array.from(firstSelect.options);
        
        // 只保留非預設選項（過濾掉 "請選擇工程類別" 選項）
        const filteredOptions = options.filter(option => 
            !option.classList.contains('dropdown-placeholder'));
        
        // 加上預設選項
        return `<option value="" class="dropdown-placeholder">請選擇工程類別</option>` + 
            filteredOptions.map(option => {
                return `<option value="${option.value}" ${option.selected ? 'selected' : ''}>${option.text}</option>`;
            }).join('');
    }
    
    // Handle form submission
    wbsQueryForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(wbsQueryForm);
        
        // Clear previous results
        queryResultsDiv.innerHTML = '';
        
        // Submit query
        fetch('/query', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Show results container
            resultsContainer.style.display = 'block';
            
            // Check if there's an error in the response
            if (data.error) {
                queryResultsDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle"></i> ${data.error}
                    </div>
                    <p class="text-secondary">請填寫至少一個完整的查詢項目</p>
                `;
                return;
            }
            
            // Process each result item
            Object.keys(data).forEach(itemKey => {
                const itemData = data[itemKey];
                const itemId = itemKey.replace('item_', '');
                const queryPath = itemData.path;
                const results = itemData.result || [];
                
                // Create a card for this item's result
                const resultCard = document.createElement('div');
                resultCard.className = 'card mb-3 result-card';
                
                // Add success/error class
                if (results.length > 0 && !results[0].error) {
                    resultCard.classList.add('success');
                } else {
                    resultCard.classList.add('error');
                }
                
                // Card header
                const cardHeader = document.createElement('div');
                cardHeader.className = 'card-header';
                cardHeader.innerHTML = `<h6 class="mb-0">WBS 項目 ${itemId}: <span class="text-info">${queryPath}</span></h6>`;
                resultCard.appendChild(cardHeader);
                
                // Card body
                const cardBody = document.createElement('div');
                cardBody.className = 'card-body';
                
                if (results.length > 0 && !results[0].error) {
                    // Success case - create table
                    const table = document.createElement('table');
                    table.className = 'table table-sm';
                    
                    // Table header
                    const thead = document.createElement('thead');
                    thead.innerHTML = `
                        <tr>
                            <th>WBS編碼</th>
                            <th>工項名稱</th>
                            <th>成本</th>
                            <th>工期(天)</th>
                        </tr>
                    `;
                    table.appendChild(thead);
                    
                    // Table body
                    const tbody = document.createElement('tbody');
                    results.forEach((result, index) => {
                        const row = document.createElement('tr');
                        row.className = index === results.length - 1 ? 'table-success' : ''; // Highlight the last row (target item)
                        row.innerHTML = `
                            <td>${result.code}</td>
                            <td>${result.name}</td>
                            <td>${result.cost}</td>
                            <td>${result.days}</td>
                        `;
                        tbody.appendChild(row);
                    });
                    table.appendChild(tbody);
                    
                    // Append table to card body
                    cardBody.appendChild(table);
                    
                    // Add path visualization
                    const pathDiv = document.createElement('div');
                    pathDiv.className = 'mt-3';
                    pathDiv.innerHTML = '<p class="text-secondary mb-2">路徑階層:</p>';
                    
                    const hierarchyDiv = document.createElement('div');
                    hierarchyDiv.className = 'ms-2';
                    
                    results.forEach((result, index) => {
                        const item = document.createElement('div');
                        item.className = 'hierarchy-item';
                        
                        // Last item is highlighted
                        const textClass = index === results.length - 1 ? 'text-success fw-bold' : 'text-secondary';
                        
                        item.innerHTML = `
                            <p class="${textClass}">
                                <i class="bi bi-arrow-right"></i> 
                                ${result.code} ${result.name}
                            </p>
                        `;
                        hierarchyDiv.appendChild(item);
                    });
                    
                    pathDiv.appendChild(hierarchyDiv);
                    cardBody.appendChild(pathDiv);
                } else {
                    // Error case
                    cardBody.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="bi bi-exclamation-triangle"></i> 
                            ${results[0]?.error || '查詢時發生錯誤'}
                        </div>
                        <p class="text-secondary">請確認選擇的工項路徑是否正確</p>
                    `;
                }
                
                resultCard.appendChild(cardBody);
                queryResultsDiv.appendChild(resultCard);
            });
            
            // Scroll to results
            resultsContainer.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(error => {
            console.error('Error:', error);
            queryResultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> 查詢時發生錯誤，請稍後再試
                </div>
            `;
            resultsContainer.style.display = 'block';
        });
    });
    
    // Toggle WBS tree visibility
    toggleWbsTreeBtn.addEventListener('click', function() {
        if (wbsTreeContainer.style.display === 'none') {
            wbsTreeContainer.style.display = 'block';
        } else {
            wbsTreeContainer.style.display = 'none';
        }
    });
    
    // Fetch and display the full WBS structure
    function fetchFullWbs() {
        fetch('/full_wbs')
            .then(response => response.json())
            .then(data => {
                wbsTreeBody.innerHTML = '';
                
                data.forEach(item => {
                    const row = document.createElement('tr');
                    
                    // Indentation based on WBS code length
                    const depth = (item.code.match(/\./g) || []).length;
                    const indentation = '&nbsp;'.repeat(depth * 4);
                    
                    row.innerHTML = `
                        <td>${item.code}</td>
                        <td>${indentation}${item.name}</td>
                        <td>${item.cost}</td>
                        <td>${item.days}</td>
                    `;
                    wbsTreeBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching WBS tree:', error);
                wbsTreeBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-danger">
                            <i class="bi bi-exclamation-triangle"></i> 
                            無法載入 WBS 結構
                        </td>
                    </tr>
                `;
            });
    }
});
