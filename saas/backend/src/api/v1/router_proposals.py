

# ============== Proposal Management API (完整功能) ==============

@api_router.get("/proposals/all")
async def get_all_proposals_detail(
    current_user: User = Depends(get_current_active_user)
):
    """获取所有提案详情（完整列表）"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')
    
    from proposal_manager import get_proposal_manager
    
    manager = get_proposal_manager()
    proposals = manager.get_all_proposals()
    stats = manager.get_statistics()
    
    return {
        "statistics": stats,
        "proposals": proposals
    }


@api_router.get("/proposals/{proposal_id}")
async def get_proposal_detail_api(
    proposal_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取单个提案详情"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')
    
    from proposal_manager import get_proposal_manager
    
    manager = get_proposal_manager()
    proposal = manager.get_proposal_detail(proposal_id)
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return proposal


@api_router.post("/proposals/{proposal_id}/approve")
async def approve_proposal_api(
    proposal_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """批准提案"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')
    
    from proposal_manager import get_proposal_manager
    
    manager = get_proposal_manager()
    success = manager.approve_proposal(proposal_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Proposal already processed")
    
    return {"message": "Proposal approved", "proposal_id": proposal_id}


@api_router.post("/proposals/{proposal_id}/reject")
async def reject_proposal_api(
    proposal_id: str,
    reason: str = "",
    current_user: User = Depends(get_current_active_user)
):
    """拒绝提案"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')
    
    from proposal_manager import get_proposal_manager
    
    manager = get_proposal_manager()
    success = manager.reject_proposal(proposal_id, reason)
    
    if not success:
        raise HTTPException(status_code=400, detail="Proposal already processed")
    
    return {"message": "Proposal rejected", "proposal_id": proposal_id}
