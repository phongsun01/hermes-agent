def _build_inline_menu_payload(level: str = 'root', data: dict = None) -> dict:
    lvl = (level or 'root').strip().lower()
    data = data or {}

    if lvl in ('root', 'main'):
        return {
            'text': '📂 **Hệ thống Quản lý Công văn Quảng Ninh**\n\nChọn một chức năng để xử lý:',
            'buttons': [
                [
                    {'text': '📋 VB mới', 'callback_data': 'v1|cc|run|list'},
                    {'text': '📅 VB hôm nay', 'callback_data': 'v1|cc|run|list_today'},
                ],
                [
                    {'text': '🎯 Chọn VB để xử lý', 'callback_data': 'v1|cc|open|select_doc'},
                ],
                [
                    {'text': '🔔 Theo dõi VB đi', 'callback_data': 'v1|cc|run|help_theodoi'},
                ],
                [
                    {'text': '🧹 Kết thúc toàn bộ', 'callback_data': 'v1|cc|run|end_all'},
                    {'text': 'ℹ️ Hướng dẫn', 'callback_data': 'v1|cc|run|help'},
                ]
            ],
            'meta': {'menu_level': 'root'}
        }
    
    elif lvl == 'select_doc':
        docs = data.get('docs', [])
        if not docs:
            return {
                'text': '📂 **Danh sách VB mới**\n\nHiện không có văn bản mới nào.',
                'buttons': [
                    [{'text': '🔙 Quay lại', 'callback_data': 'v1|cc|open|root'}]
                ],
                'meta': {'menu_level': 'select_doc'}
            }
        
        buttons = []
        # Pair them 2 per row
        row = []
        for doc_id in docs:
            row.append({'text': f'📄 #{doc_id}', 'callback_data': f'v1|cc|open|doc|{doc_id}'})
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
            
        buttons.append([{'text': '🔙 Quay lại', 'callback_data': 'v1|cc|open|root'}])
        
        return {
            'text': '📂 **Danh sách VB mới**\n\nChọn một văn bản để thao tác:',
            'buttons': buttons,
            'meta': {'menu_level': 'select_doc'}
        }
        
    elif lvl == 'doc':
        doc_id = data.get('doc_id')
        return {
            'text': f'📄 **Thao tác với Văn bản #{doc_id}**\n\nChọn hành động:',
            'buttons': [
                [
                    {'text': '⬇️ Tải file', 'callback_data': f'v1|cc|run|tai|{doc_id}'},
                    {'text': '📝 Tóm tắt', 'callback_data': f'v1|cc|run|tomtat|{doc_id}'},
                ],
                [
                    {'text': '📄 Dự thảo', 'callback_data': f'v1|cc|run|duthao|{doc_id}'},
                    {'text': '✅ Kết thúc', 'callback_data': f'v1|cc|run|end|{doc_id}'},
                ],
                [
                    {'text': '🔙 Quay lại danh sách', 'callback_data': 'v1|cc|open|select_doc'}
                ]
            ],
            'meta': {'menu_level': 'doc', 'doc_id': doc_id}
        }
    
    return {}
