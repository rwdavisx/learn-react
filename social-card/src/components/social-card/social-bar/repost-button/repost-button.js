import React, { Component } from 'react';
import {MdSync} from 'react-icons/lib/md'
import './repost-button.css';

class RepostButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
            amount: isNaN(this.props.num) || this.props.num === null ? 0 : this.props.num,
        }
    };

    render() {
        return (
        <div className={'repost-btn'} onClick={() => this.handleRepost()}>
            <MdSync /><span>{this.state.amount}</span>
        </div>
        );
    };

    handleRepost() {
        let amt = this.state.amount;
        this.setState({amount: amt += 1});
    };
};

export default RepostButton;
