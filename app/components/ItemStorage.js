'use client'

import { useState, useEffect } from 'react'
import { supabase } from '../../lib/supabase'

export default function ItemStorage() {
  const [items, setItems] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false)
  const [passwordInput, setPasswordInput] = useState('')
  const [passwordError, setPasswordError] = useState(false)
  const [itemToUnlock, setItemToUnlock] = useState(null)
  const [unlockedItems, setUnlockedItems] = useState(new Set())
  const [editingItem, setEditingItem] = useState(null)
  const [formData, setFormData] = useState({ title: '', content: '', password: '' })
  const [deleteConfirmItem, setDeleteConfirmItem] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [lastCommit, setLastCommit] = useState(null)

  useEffect(() => {
    fetchItems()
    fetchLastCommit()
  }, [])

  async function fetchLastCommit() {
    try {
      const response = await fetch('https://api.github.com/repos/Bjornh-cmd/database/commits/master')
      if (response.ok) {
        const data = await response.json()
        setLastCommit({
          date: new Date(data.commit.committer.date).toLocaleString('nl-NL'),
          message: data.commit.message,
          url: data.html_url
        })
      }
    } catch (error) {
      console.error('Error fetching commit:', error)
    }
  }

  async function fetchItems() {
    const { data, error } = await supabase
      .from('items')
      .select('*')
      .order('created_at', { ascending: false })
    
    if (error) {
      console.error('Error fetching items:', error.message, error.details, error.hint)
      setErrorMessage(`Failed to load items: ${error.message || 'Table may not exist. Please create the items table in Supabase.'}`)
      return
    }
    
    setErrorMessage(null)
    setItems(data || [])
  }

  const filteredItems = items.filter(item =>
    item.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  function handleItemClick(item) {
    if (item.password && !unlockedItems.has(item.id)) {
      setItemToUnlock(item)
      setIsPasswordModalOpen(true)
      setPasswordInput('')
      setPasswordError(false)
    } else {
      setSelectedItem(item)
    }
  }

  function checkPassword() {
    if (itemToUnlock && passwordInput === itemToUnlock.password) {
      setUnlockedItems(prev => new Set([...prev, itemToUnlock.id]))
      setIsPasswordModalOpen(false)
      setSelectedItem(itemToUnlock)
      setItemToUnlock(null)
      setPasswordError(false)
    } else {
      setPasswordError(true)
    }
  }

  function openCreateModal() {
    setEditingItem(null)
    setFormData({ title: '', content: '', password: '' })
    setIsModalOpen(true)
  }

  function openEditModal(item, e) {
    e.stopPropagation()
    setEditingItem(item)
    const content = item.content || (item.content_rows ? item.content_rows.join('\n\n') : '')
    setFormData({
      title: item.title,
      content: content,
      password: item.password || ''
    })
    setIsModalOpen(true)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    
    const itemData = {
      title: formData.title,
      content: formData.content,
      password: formData.password || null
    }

    if (editingItem) {
      const { error } = await supabase
        .from('items')
        .update(itemData)
        .eq('id', editingItem.id)
      
      if (error) {
        console.error('Error updating item:', error.message, error.details, error.hint)
        return
      }
    } else {
      const { error } = await supabase
        .from('items')
        .insert([itemData])
      
      if (error) {
        console.error('Error creating item:', error.message, error.details, error.hint, error.code)
        return
      }
    }

    setIsModalOpen(false)
    fetchItems()
  }

  async function handleDelete(item, e) {
    e.stopPropagation()
    setDeleteConfirmItem(item)
  }

  async function confirmDelete() {
    if (!deleteConfirmItem) return
    
    const { error } = await supabase
      .from('items')
      .delete()
      .eq('id', deleteConfirmItem.id)
    
    if (error) {
      console.error('Error deleting item:', error.message, error.details, error.hint)
      return
    }

    if (selectedItem?.id === deleteConfirmItem.id) {
      setSelectedItem(null)
    }
    
    setUnlockedItems(prev => {
      const newSet = new Set(prev)
      newSet.delete(deleteConfirmItem.id)
      return newSet
    })
    
    setDeleteConfirmItem(null)
    fetchItems()
  }

  return (
    <div style={styles.container}>
      <div style={styles.sidebar}>
        <div style={styles.header}>
          <h1 style={styles.title}>My Items</h1>
          <button onClick={openCreateModal} style={styles.addButton}>
            + Add Item
          </button>
        </div>

        <input
          type="text"
          placeholder="Search items..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={styles.searchInput}
        />

        {errorMessage && (
          <div style={styles.errorBanner}>{errorMessage}</div>
        )}

        <div style={styles.itemList}>
          {filteredItems.map(item => (
            <div
              key={item.id}
              onClick={() => handleItemClick(item)}
              style={{
                ...styles.itemCard,
                ...(selectedItem?.id === item.id ? styles.itemCardSelected : {})
              }}
            >
              <div style={styles.itemHeader}>
                <span style={styles.itemTitle}>{item.title}</span>
                {item.password && <span style={styles.lockIcon}>🔒</span>}
              </div>
              <div style={styles.itemActions}>
                <button
                  onClick={(e) => openEditModal(item, e)}
                  style={styles.actionButton}
                >
                  Edit
                </button>
                <button
                  onClick={(e) => handleDelete(item, e)}
                  style={styles.deleteButton}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          
          {filteredItems.length === 0 && (
            <div style={styles.emptyState}>No items found</div>
          )}
        </div>
      </div>

      <div style={styles.content}>
        {selectedItem ? (
          <div style={styles.contentBox}>
            <h2 style={styles.contentTitle}>{selectedItem.title}</h2>
            {(selectedItem.content || '').split('\n').filter(line => line.trim() !== '').map((line, index) => (
              <div key={index} style={styles.contentLine}>{line}</div>
            ))}
          </div>
        ) : (
          <div style={styles.emptyContent}>
            <p>Select an item to view its content</p>
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {isModalOpen && (
        <div style={styles.modalOverlay} onClick={() => setIsModalOpen(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 style={styles.modalTitle}>
              {editingItem ? 'Edit Item' : 'Create New Item'}
            </h2>
            <form onSubmit={handleSubmit} style={styles.form}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const textarea = e.target
                      const cursorPos = textarea.selectionStart
                      const text = formData.content
                      const lines = text.substring(0, cursorPos).split('\n')
                      const currentLine = lines[lines.length - 1]
                      
                      // Check for list patterns: -, *, 1., 2., etc.
                      const listMatch = currentLine.match(/^(\s*)([-*]|\d+\.)\s/)
                      if (listMatch) {
                        e.preventDefault()
                        const indent = listMatch[1]
                        const prefix = listMatch[2]
                        let newPrefix = prefix
                        
                        // If numbered list, increment the number
                        if (/^\d+\.$/.test(prefix)) {
                          newPrefix = (parseInt(prefix) + 1) + '.'
                        }
                        
                        const beforeCursor = text.substring(0, cursorPos)
                        const afterCursor = text.substring(cursorPos)
                        const newText = beforeCursor + '\n' + indent + newPrefix + ' ' + afterCursor
                        
                        setFormData({ ...formData, content: newText })
                        
                        // Set cursor position after the new prefix
                        setTimeout(() => {
                          const newCursorPos = cursorPos + 1 + indent.length + newPrefix.length + 1
                          textarea.setSelectionRange(newCursorPos, newCursorPos)
                        }, 0)
                      }
                    }
                  }}
                  required
                  rows={6}
                  style={styles.textarea}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  Password (optional)
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="Leave empty for no password"
                  style={styles.input}
                />
              </div>
              <div style={styles.modalActions}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={styles.cancelButton}
                >
                  Cancel
                </button>
                <button type="submit" style={styles.submitButton}>
                  {editingItem ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Modal */}
      {isPasswordModalOpen && (
        <div style={styles.modalOverlay} onClick={() => setIsPasswordModalOpen(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 style={styles.modalTitle}>Enter Password</h2>
            <p style={styles.passwordHint}>This item is password protected</p>
            <div style={styles.formGroup}>
              <input
                type="password"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                placeholder="Password"
                onKeyDown={(e) => e.key === 'Enter' && checkPassword()}
                style={{
                  ...styles.input,
                  ...(passwordError ? styles.inputError : {})
                }}
              />
              {passwordError && (
                <span style={styles.errorText}>Incorrect password</span>
              )}
            </div>
            <div style={styles.modalActions}>
              <button
                onClick={() => setIsPasswordModalOpen(false)}
                style={styles.cancelButton}
              >
                Cancel
              </button>
              <button onClick={checkPassword} style={styles.submitButton}>
                Unlock
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmItem && (
        <div style={styles.modalOverlay} onClick={() => setDeleteConfirmItem(null)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 style={styles.modalTitle}>Confirm Delete</h2>
            <p style={styles.deleteText}>
              Are you sure you want to delete "{deleteConfirmItem.title}"?
            </p>
            <div style={styles.modalActions}>
              <button
                onClick={() => setDeleteConfirmItem(null)}
                style={styles.cancelButton}
              >
                Cancel
              </button>
              <button onClick={confirmDelete} style={styles.deleteConfirmButton}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      {lastCommit && (
        <div style={styles.footer}>
          <span style={styles.footerText}>Laatste wijziging: {lastCommit.date}</span>
          <a href={lastCommit.url} target="_blank" rel="noopener noreferrer" style={styles.footerLink}>
            {lastCommit.message}
          </a>
        </div>
      )}
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    height: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  sidebar: {
    width: '320px',
    backgroundColor: '#f5f5f5',
    borderRight: '1px solid #e0e0e0',
    display: 'flex',
    flexDirection: 'column',
    padding: '20px 20px 50px 20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: 600,
    color: '#333',
  },
  addButton: {
    backgroundColor: '#4CAF50',
    color: 'white',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
  },
  searchInput: {
    padding: '10px 14px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '14px',
    marginBottom: '16px',
    outline: 'none',
  },
  itemList: {
    flex: 1,
    overflowY: 'auto',
  },
  itemCard: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '14px',
    marginBottom: '10px',
    cursor: 'pointer',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    transition: 'all 0.2s',
  },
  itemCardSelected: {
    boxShadow: '0 0 0 2px #4CAF50',
  },
  itemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  itemTitle: {
    fontWeight: 500,
    color: '#333',
    fontSize: '15px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  lockIcon: {
    fontSize: '14px',
  },
  itemActions: {
    display: 'flex',
    gap: '8px',
  },
  actionButton: {
    backgroundColor: '#e3f2fd',
    color: '#1976d2',
    border: 'none',
    padding: '4px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
  },
  deleteButton: {
    backgroundColor: '#ffebee',
    color: '#c62828',
    border: 'none',
    padding: '4px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
  },
  emptyState: {
    textAlign: 'center',
    color: '#999',
    padding: '40px 20px',
    fontSize: '14px',
  },
  content: {
    flex: 1,
    padding: '40px 40px 60px 40px',
    overflowY: 'auto',
    backgroundColor: '#fff',
  },
  contentBox: {
    maxWidth: '800px',
    margin: '0 auto',
  },
  contentTitle: {
    margin: '0 0 24px 0',
    fontSize: '28px',
    fontWeight: 600,
    color: '#333',
  },
  contentText: {
    fontSize: '16px',
    lineHeight: 1.7,
    color: '#444',
    whiteSpace: 'pre-wrap',
  },
  contentLine: {
    fontSize: '16px',
    lineHeight: 1.6,
    color: '#444',
    marginBottom: '12px',
    padding: '12px 16px',
    backgroundColor: '#f5f5f5',
    borderRadius: '8px',
    borderLeft: '4px solid #4CAF50',
  },
  emptyContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#999',
    fontSize: '16px',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '24px',
    width: '100%',
    maxWidth: '450px',
    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
  },
  modalTitle: {
    margin: '0 0 20px 0',
    fontSize: '20px',
    fontWeight: 600,
    color: '#333',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#555',
  },
  input: {
    padding: '10px 14px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
  },
  inputError: {
    borderColor: '#c62828',
  },
  errorText: {
    color: '#c62828',
    fontSize: '12px',
  },
  textarea: {
    padding: '10px 14px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '8px',
  },
  cancelButton: {
    backgroundColor: '#f5f5f5',
    color: '#666',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
  },
  submitButton: {
    backgroundColor: '#4CAF50',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
  },
  deleteConfirmButton: {
    backgroundColor: '#c62828',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
  },
  passwordHint: {
    margin: '-10px 0 16px 0',
    color: '#666',
    fontSize: '14px',
  },
  deleteText: {
    margin: '0 0 20px 0',
    color: '#555',
    fontSize: '15px',
  },
  errorBanner: {
    backgroundColor: '#ffebee',
    color: '#c62828',
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '16px',
    fontSize: '13px',
    border: '1px solid #ef5350',
  },
  footer: {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    borderTop: '2px solid #4CAF50',
    padding: '12px 20px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '12px',
    fontSize: '13px',
    boxShadow: '0 -2px 10px rgba(0,0,0,0.1)',
    zIndex: 100,
  },
  footerText: {
    color: '#555',
    fontWeight: 500,
  },
  footerLink: {
    color: '#1976d2',
    textDecoration: 'none',
    fontWeight: 600,
    maxWidth: '400px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
}
