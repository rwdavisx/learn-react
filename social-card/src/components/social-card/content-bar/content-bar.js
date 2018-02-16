import React, { Component } from 'react';
import { FaUser, FaCaretSquareODown } from 'react-icons/lib/fa';

import './content-bar.css';

class ContentBar extends Component {
    constructor(props) {
        super(props);
        this.state = {
            userId: this.props.userId,
            fullName: this.props.fullName,
            text: this.props.text,
            date: this.props.date,
        }
    };

    render() {
        return (
            <div className={'container-fluid mb-1'}>
                <div className='row'>
                    <div className='col-2'>
                        <span onClick={this.handleComment('user')}>
                            <FaUser size={36} />
                        </span>
                    </div>
                    <div className='col-8 text-left'>
                        <span className={'font-weight-bold'}>{this.state.fullName}</span> <span className={'text-muted'}><a>@{this.state.userId}</a></span> <span className={'text-muted'}>- {this.state.date}</span>
                        <p>{this.state.text}</p>
                    </div>
                    <div className='col-2 d-flex justify-content-end'>
                        <span onClick={this.handleComment('collapse')}>
                            <FaCaretSquareODown size={18} color={'#888888AA'} />
                        </span>
                    </div>
                </div>
            </div>
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default ContentBar;